import time

import anthropic
from pydantic import BaseModel, ValidationError

from . import tracking
from .config import settings

_client = anthropic.Anthropic(api_key=settings.anthropic_api_key, max_retries=2)

# These models reject forced tool_choice ({"type": "tool"} or {"type": "any"}) outright.
# Fall back to tool_choice "auto" + an explicit instruction to always call the tool.
NO_FORCED_TOOL_CHOICE = {"claude-opus-5-5", "claude-fable-5-1", "claude-mythos-5-1"}


def call_structured(*, name: str, model: str, system: str, messages: list[dict],
                    schema: type[BaseModel], max_tokens: int = 4096,
                    cache_system: bool = False) -> BaseModel:
    tracking.check_budget()
    forced = model not in NO_FORCED_TOOL_CHOICE
    tool_choice = {"type": "tool", "name": "submit"} if forced else {"type": "auto"}
    tool_desc = "Submit the final structured result."
    if not forced:
        system = system + "\n\nYou MUST respond by calling the `submit` tool exactly once with your answer. Do not reply in plain text."

    tool = {"name": "submit", "description": tool_desc, "input_schema": schema.model_json_schema()}
    block = {"type": "text", "text": system}
    if cache_system:
        block["cache_control"] = {"type": "ephemeral"}

    err = None
    for _ in range(2):
        t0 = time.perf_counter()
        resp = _client.messages.create(
            model=model, max_tokens=max_tokens, system=[block], messages=messages,
            tools=[tool], tool_choice=tool_choice)
        ms = (time.perf_counter() - t0) * 1000
        u = resp.usage
        tool_uses = [b for b in resp.content if b.type == "tool_use"]
        if not tool_uses:
            err = ValueError("Model did not call the submit tool")
            ok = False
        else:
            try:
                out, ok = schema.model_validate(tool_uses[0].input), True
            except ValidationError as e:
                out, ok, err = None, False, e
        tracking.log_llm(
            name=name, model=model, input_tokens=u.input_tokens, output_tokens=u.output_tokens,
            cache_read=getattr(u, "cache_read_input_tokens", 0) or 0,
            cache_write=getattr(u, "cache_creation_input_tokens", 0) or 0,
            latency_ms=ms, ok=ok)
        if ok:
            return out
        messages = [*messages, {"role": "user",
                                "content": f"Your output failed validation:\n{err}\nCall submit again with a valid result."}]
    raise err