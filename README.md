# AI Travel Planner

A retrieval-grounded, evaluated, cost-tracked itinerary planner built with FastAPI, Claude, and the Google Maps Platform. Every place the LLM can recommend is a real, verified location -- never hallucinated -- and every LLM/API call is logged with cost and latency.

## Why this exists

Most AI trip planner demos let an LLM invent an itinerary from memory, with no way to know whether the places it names are real, open, or reachable in the time given. This project takes a different approach: retrieve first, then let the LLM plan only over what was retrieved.

1. Parse a free-text or structured trip request
2. Pull real candidate places from Google Places API (New) -- real coordinates, hours, ratings
3. Claude builds an itinerary referencing only those retrieved places
4. A deterministic validator checks the plan against real opening hours, real travel times, pace limits, and budget -- and feeds any violations back to Claude for automatic repair
5. Every step is logged: tokens, cost, latency, cache hits

Because the LLM can only reference retrieved place IDs, hallucinated venues are structurally impossible -- not just discouraged by a system prompt.

## Architecture

    User request
       -> Parse (Haiku, structured output)
       -> Retrieve candidates (Google Places API, cached)
       -> Plan (Sonnet, forced-tool structured output)
       -> Validate (hours / pace / travel-time / budget checks against real Routes data)
       -> Repair loop (up to 2 rounds, violations fed back to the model)
       -> Enrich (real coordinates, addresses, travel legs)
       -> Response + full cost/latency trace

Every LLM call and every Maps API call is logged to SQLite with token counts, dollar cost, and latency, and cached where Google's terms allow, so repeated development/eval runs don't re-pay for identical retrieval.

## Current baseline results

Measured across 20 diverse test cases (varied cities, budgets, paces, trip lengths, and one adversarial prompt-injection case), using Claude Sonnet for planning and Claude Opus for LLM-judged quality scoring.

Metric | Value
---|---
First-pass constraint satisfaction | 0%
Final constraint satisfaction (after repair loop) | ~65%
Average repair rounds used | 1.7
Mean cost per itinerary | $0.14
p95 cost per itinerary | $0.32
Median latency | ~25s
p95 latency | ~73s
Judge score -- interest match (1-5) | 2.7
Judge score -- geographic coherence (1-5) | 3.1
Judge score -- pacing realism (1-5) | 2.1
Prompt-injection success rate | 0%

Reading these honestly: the 0% first-pass satisfaction rate reflects how tightly the validator checks real-world constraints (exact opening hours, real travel times, pace limits) -- Claude reliably violates at least one of these on the first attempt across every test case, and the repair loop recovers roughly two-thirds of cases to a fully valid plan. The remaining gap, concentrated in longer (5-7 day) packed itineraries, is the active area of optimization (see Roadmap below).

## Known issues and what I'm working on

Building this surfaced several real bugs worth documenting, since diagnosing them was as instructive as writing the happy path.

- Claude Opus 5.5 rejects forced tool_choice outright -- a model-specific API change not present in Sonnet/Haiku. Fixed with a per-model fallback to tool_choice auto plus an explicit instruction to always call the submit tool.
- SQLite connections were leaking file descriptors -- using a Connection as a context manager only manages the transaction, not the connection lifetime. Under parallel eval runs this exhausted the OS file-descriptor limit. Fixed with an explicit contextmanager wrapper that closes the connection.
- httpx.post opened a fresh TCP connection per call instead of reusing one -- compounded the file-descriptor issue under load. Fixed with a shared, reused httpx.Client.
- A stale thread-local run ID caused false-positive budget rejections: in a multi-threaded eval runner, a worker thread's current-run context wasn't cleared after a run finished, so a later judge call on that same thread was checked against a previous, already-expensive run's budget. Fixed by clearing the context on run completion and adding a null-check guard.
- Occasional schema-shape drift from the model: Claude sometimes returns a nested JSON structure as a string, wraps it in an extra key, or truncates the last field of a long structured output under token pressure. Handled with tolerant field validators that unwrap or repair these shapes rather than hard-failing.
- Constraint satisfaction degrades on long, packed itineraries -- more stops means more chances for a hard violation, and the current repair-round ceiling isn't always enough to clear them all. This is the next optimization target.

## Eval methodology

- 20 hand-built test cases spanning: popular cities, small towns and islands, niche interests such as birdwatching and vintage shopping, budget-versus-interest conflicts, weekday-hazard cases like Monday museum closures, non-English destination names, and one deliberate prompt-injection attempt.
- Deterministic metrics (constraint satisfaction, hours violations, travel feasibility, duplicates) are computed by the same validator that gates production repairs, not a separate, looser check.
- LLM-judged quality (interest match, geographic coherence, variety, pacing realism, rationale quality) is scored 1-5 by Claude Opus, a different and stronger model than the planner, to reduce self-preference bias.
- Every run's cost and latency is logged automatically, and aggregate stats such as mean and p95 are computed per eval run and comparable across prompt or model changes.

## Stack

- Backend: Python, FastAPI, Pydantic v2, Anthropic SDK, SQLite
- Grounding: Google Places API (New), Google Routes API
- Frontend: in progress -- Next.js, TypeScript, Google Maps JS API
- CI: GitHub Actions running lint, tests, and an eval regression gate

## Running it locally

    cd backend
    python3 -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env
    uvicorn app.main:app --reload

Then visit http://127.0.0.1:8000/docs for the interactive API, or POST to /api/plan with a body like:

    {
      "destination": "Lisbon, Portugal",
      "days": 2,
      "start_date": "2026-11-02",
      "budget_level": "moderate",
      "interests": ["food", "history"],
      "pace": "balanced"
    }

Run the eval suite:

    python3 -m evals.run_evals --subset smoke
    python3 -m evals.run_evals --judge

## Roadmap

- Raise the repair-round limit and/or improve the repair prompt specifically for long, packed itineraries
- Next.js frontend: map view, day-by-day timeline, live cost and latency trace panel
- Model-cascade experiment: cheap-model draft, escalate to a stronger model only when violations remain
- Candidate-set pruning to reduce token cost without hurting satisfaction
- Deploy to Fly.io or Render plus Vercel, with rate limiting and spend caps
