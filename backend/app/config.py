from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    anthropic_api_key: str
    google_maps_api_key: str
    planner_model: str = "claude-sonnet-5"
    parser_model: str = "claude-haiku-4-5-20251001"
    judge_model: str = "claude-opus-5-5"
    db_path: str = "travel.db"
    max_run_cost_usd: float = 0.50
    max_repairs: int = 2

settings = Settings()
