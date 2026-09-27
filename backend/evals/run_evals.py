import argparse
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app import tracking
from app.planner import plan_trip
from app.schemas import TripRequest
from evals.judge import judge


def run_case(case: dict, tag: str, use_judge: bool) -> dict:
    req = TripRequest(**case["request"])
    try:
        resp = plan_trip(req, tag=tag)
    except Exception as e:  # noqa: BLE001 - any failure here is a real per-case result, not a crash
        return {"id": case["id"], "tags": case.get("tags", []), "error": repr(e)}

    hard_codes = [v.code for v in resp.violations if v.severity == "hard"]
    n_stops = sum(len(d.stops) for d in resp.days) or 1
    row = {
        "id": case["id"],
        "tags": case.get("tags", []),
        "final_ok": not hard_codes,
        "first_pass_ok": resp.metrics.first_pass_hard_violations == 0,
        "final_violation_codes": hard_codes,
        "n_stops": n_stops,
        **resp.metrics.model_dump(),
    }
    if use_judge:
        try:
            row["judge"] = judge(req, resp).model_dump()
        except Exception as e:  # noqa: BLE001 - judge failure shouldn't kill the whole eval row
            row["judge_error"] = repr(e)
    return row


def aggregate(rows: list[dict]) -> dict:
    ok = [r for r in rows if "error" not in r]
    if not ok:
        return {"n": len(rows), "errors": len(rows), "note": "all cases errored"}

    def m(key):
        return statistics.mean(r[key] for r in ok)

    lat_sorted = sorted(r["latency_ms"] for r in ok)
    cost_sorted = sorted(r["cost_usd"] for r in ok)
    judged = [r for r in ok if "judge" in r]

    out = {
        "n": len(rows),
        "errors": len(rows) - len(ok),
        "first_pass_satisfaction": m("first_pass_ok"),
        "final_satisfaction": m("final_ok"),
        "avg_repair_rounds": m("repair_rounds"),
        "cost_mean": m("cost_usd"),
        "cost_p95": cost_sorted[min(len(cost_sorted) - 1, int(len(cost_sorted) * 0.95))],
        "latency_p50_ms": lat_sorted[len(lat_sorted) // 2],
        "latency_p95_ms": lat_sorted[min(len(lat_sorted) - 1, int(len(lat_sorted) * 0.95))],
    }
    if judged:
        out["judge_mean"] = {
            k: statistics.mean(r["judge"][k] for r in judged)
            for k in ("interest_match", "geographic_coherence", "variety", "pacing_realism", "rationale_quality")
        }
        out["n_judged"] = len(judged)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default=f"eval-{int(time.time())}")
    ap.add_argument("--subset", choices=["smoke", "all"], default="all")
    ap.add_argument("--judge", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--compare", default=None)
    ap.add_argument("--fail-on-regress", action="store_true")
    args = ap.parse_args()

    tracking.init_db()
    cases_path = Path(__file__).parent / "cases.jsonl"
    cases = [json.loads(line) for line in cases_path.read_text().splitlines() if line.strip()]
    if args.subset == "smoke":
        cases = [c for c in cases if "smoke" in c.get("tags", [])]

    print(f"Running {len(cases)} cases (tag={args.tag}, judge={args.judge})...")
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(lambda c: run_case(c, args.tag, args.judge), cases))

    agg = aggregate(rows)
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)
    out_path = results_dir / f"{args.tag}.json"
    out_path.write_text(json.dumps({"aggregate": agg, "rows": rows}, indent=2, default=str))

    print(json.dumps(agg, indent=2))
    print(f"\nSaved to {out_path}")

    for r in rows:
        if "error" in r:
            print(f"  ERROR [{r['id']}]: {r['error']}")

    if args.compare:
        base = json.loads(Path(args.compare).read_text())["aggregate"]
        problems = []
        if agg.get("final_satisfaction", 1) < base.get("final_satisfaction", 0) - 0.05:
            problems.append("constraint satisfaction dropped >5pts")
        if agg.get("cost_mean", 0) > base.get("cost_mean", float("inf")) * 1.25:
            problems.append("mean cost up >25%")
        if agg.get("latency_p95_ms", 0) > base.get("latency_p95_ms", float("inf")) * 1.5:
            problems.append("p95 latency up >50%")
        if problems:
            print("\nREGRESSIONS DETECTED:")
            for p in problems:
                print(f"  - {p}")
            if args.fail_on_regress:
                raise SystemExit(1)


if __name__ == "__main__":
    main()