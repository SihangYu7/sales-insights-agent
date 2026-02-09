import os


def get_auth_database_url() -> str:
    return os.getenv("AUTH_DATABASE_URL", os.getenv("DATABASE_URL", "sqlite:///sales.db"))


def get_analytics_backend() -> str:
    analytics_backend = os.getenv("ANALYTICS_BACKEND", "").strip().lower()
    if not analytics_backend:
        analytics_backend = (
            "databricks"
            if os.getenv("USE_DATABRICKS", "false").lower() == "true"
            else "sqlite"
        )
    return analytics_backend


def get_openai_model(default: str = "gpt-3.5-turbo") -> str:
    return os.getenv("OPENAI_MODEL", default)


def use_responses_api() -> bool:
    return os.getenv("OPENAI_USE_RESPONSES", "false").lower() == "true"


def use_dev_seed() -> bool:
    return os.getenv("DEV_SEED", "false").lower() == "true"
