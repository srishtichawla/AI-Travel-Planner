from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from . import parser, planner, tracking
from .schemas import PlanResponse, TripRequest


@asynccontextmanager
async def lifespan(app: FastAPI):
    tracking.init_db()
    yield


app = FastAPI(title="AI Travel Planner", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"],
                   allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/api/parse", response_model=TripRequest)
def parse(body: dict):
    return parser.parse_request(body["text"])


@app.post("/api/plan", response_model=PlanResponse)
def plan(req: TripRequest):
    return planner.plan_trip(req)