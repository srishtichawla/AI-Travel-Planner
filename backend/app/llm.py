import time

import anthropic
from pydantic import BaseModel, ValidationError

from . import tracking
from .config import settings

_client = anthropic.Anthropic(api_key=settings.anthropic_api_key, max_retries=2)

def call_structured(*, name: str, model: str, system: str, messages: list[dict],
                    schema: type[BaseModel], max_tokens: int = 4096,
                    cache_system: bool = False) -> BaseModel:
    tracking.check_budget()
    tool = {"name": "submit", "description": "Submit the final structured result.",
            "input_schema": schema.model_json_schema()}
    block = {"type": "text", "text": system}
    if cache_system:
        block["cache_control"] = {"type": "ephemeral"}

    err = None
    for _ in range(2):
        t0 = time.perf_counter()
        resp = _client.messages.create(
            model=model, max_tokens=max_tokens, system=[block], messages=messages,
            tools=[tool], tool_choice={"type": "tool", "name": "submit"})
        ms = (time.perf_counter() - t0) * 1000
        u = resp.usage
        tu = next(b for b in resp.content if b.type == "tool_use")
        try:
            out, ok = schema.model_validate(tu.input), True
        except ValidationError as e:
            out, ok, err = None, False, e
        tracking.log_llm(
            name=name, model=model, input_tokens=u.input_tokens, output_tokens=u.output_tokens,
            cache_read=getattr(u, "cache_read_input_tokens", 0) or 0,
            cache_write=getattr(u, "cache_creation_input_tokens", 0) or 0,
            latency_ms=ms, ok=ok)
        if ok:
            return out
        messages = messages + [{"role": "user",
                                "content": f"Your output failed validation:\n{err}\nCall submit again with a valid result."}]
    raise err