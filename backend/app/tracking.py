import contextvars, sqlite3, time, uuid
from contextlib import contextmanager
from .config import settings
from .schemas import RunMetrics

_run_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("run_id", default=None)

# USD per million tokens (input, output). VERIFY against anthropic.com/pricing before trusting numbers.
LLM_PRICES = {
    "claude-haiku-4-5-20251001": (1.00, 5.00),
    "claude-sonnet-5": (3.00, 15.00),
    "claude-opus-5-5": (5.00, 25.00),
}
CACHE_READ_MULT, CACHE_WRITE_MULT = 0.10, 1.25

# USD per request, estimates. VERIFY against Google Maps Platform pricing.
MAPS_PRICES = {"places_text_search": 0.035, "routes_compute": 0.005}

class BudgetExceeded(RuntimeError):
    ...

def _conn():
    c = sqlite3.connect(settings.db_path)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS runs(
          id TEXT PRIMARY KEY, created_at REAL, tag TEXT, request_json TEXT,
          ok INTEGER, total_cost REAL, total_ms REAL, repair_rounds INTEGER,
          first_pass_hard INTEGER);
        CREATE TABLE IF NOT EXISTS calls(
          id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, kind TEXT, name TEXT, model TEXT,
          input_tokens INTEGER, output_tokens INTEGER, cache_read_tokens INTEGER,
          cache_write_tokens INTEGER, cost_usd REAL, latency_ms REAL,
          cache_hit INTEGER, ok INTEGER, created_at REAL);
        CREATE TABLE IF NOT EXISTS cache(key TEXT PRIMARY KEY, value TEXT, expires REAL);
        """)

def start_run(req, tag: str | None = None) -> str:
    init_db()
    rid = uuid.uuid4().hex[:12]
    _run_id.set(rid)
    with _conn() as c:
        c.execute("INSERT INTO runs(id,created_at,tag,request_json) VALUES(?,?,?,?)",
                  (rid, time.time(), tag, req.model_dump_json()))
    return rid

def current_run() -> str | None:
    return _run_id.get()

def set_run(rid: str | None):
    _run_id.set(rid)

def llm_cost(model, in_tok, out_tok, cache_read=0, cache_write=0) -> float:
    pin, pout = LLM_PRICES.get(model, (0.0, 0.0))
    return (in_tok * pin + out_tok * pout
            + cache_read * pin * CACHE_READ_MULT
            + cache_write * pin * CACHE_WRITE_MULT) / 1e6

def _insert(**k):
    with _conn() as c:
        c.execute("""INSERT INTO calls(run_id,kind,name,model,input_tokens,output_tokens,
          cache_read_tokens,cache_write_tokens,cost_usd,latency_ms,cache_hit,ok,created_at)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
          (current_run(), k["kind"], k["name"], k.get("model"), k.get("input_tokens", 0),
           k.get("output_tokens", 0), k.get("cache_read", 0), k.get("cache_write", 0),
           k.get("cost_usd", 0.0), k.get("latency_ms", 0.0), int(k.get("cache_hit", False)),
           int(k.get("ok", True)), time.time()))

def log_llm(*, name, model, input_tokens, output_tokens, cache_read, cache_write, latency_ms, ok):
    _insert(kind="llm", name=name, model=model, input_tokens=input_tokens,
            output_tokens=output_tokens, cache_read=cache_read, cache_write=cache_write,
            cost_usd=llm_cost(model, input_tokens, output_tokens, cache_read, cache_write),
            latency_ms=latency_ms, ok=ok)

def log_cache_hit(kind, name):
    _insert(kind=kind, name=name, cache_hit=True)

@contextmanager
def track_maps(name: str):
    t0, ok = time.perf_counter(), True
    try:
        yield
    except Exception:
        ok = False
        raise
    finally:
        _insert(kind="maps", name=name, cost_usd=MAPS_PRICES.get(name, 0.0),
                latency_ms=(time.perf_counter() - t0) * 1000, ok=ok)

def run_cost(rid: str | None = None) -> float:
    with _conn() as c:
        r = c.execute("SELECT COALESCE(SUM(cost_usd),0) s FROM calls WHERE run_id=?",
                      (rid or current_run(),)).fetchone()
    return r["s"]

def check_budget():
    if run_cost() > settings.max_run_cost_usd:
        raise BudgetExceeded(f"run exceeded ${settings.max_run_cost_usd}")

def finish_run(rid, *, ok, total_ms, repair_rounds, first_pass_hard) -> RunMetrics:
    with _conn() as c:
        agg = c.execute("""SELECT COALESCE(SUM(cost_usd),0) cost,
              SUM(kind='llm') llm, SUM(kind='maps' AND cache_hit=0) maps, SUM(cache_hit) hits
              FROM calls WHERE run_id=?""", (rid,)).fetchone()
        c.execute("UPDATE runs SET ok=?,total_cost=?,total_ms=?,repair_rounds=?,first_pass_hard=? WHERE id=?",
                  (int(ok), agg["cost"], total_ms, repair_rounds, first_pass_hard, rid))
    return RunMetrics(run_id=rid, cost_usd=agg["cost"], latency_ms=total_ms, llm_calls=agg["llm"] or 0,
                      maps_calls=agg["maps"] or 0, cache_hits=agg["hits"] or 0,
                      repair_rounds=repair_rounds, first_pass_hard_violations=first_pass_hard)