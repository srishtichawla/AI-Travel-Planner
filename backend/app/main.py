from fastapi import FastAPI

app = FastAPI(title="AI Travel Planner")

@app.get("/health")
def health():
    return {"ok": True}
