import os
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        raise RuntimeError(f"Missing required env var: {key}")
    return val


DATABASE_URL: str = _require("DATABASE_URL")
TELEGRAM_BOT_TOKEN: str = _require("TELEGRAM_BOT_TOKEN")
TELEGRAM_WEBHOOK_SECRET: str = _require("TELEGRAM_WEBHOOK_SECRET")
TELEGRAM_ALLOWED_ID: int = int(_require("TELEGRAM_ALLOWED_ID"))
GROQ_API_KEY: str = _require("GROQ_API_KEY")
OPENROUTER_API_KEY: str = os.environ.get("OPENROUTER_API_KEY", "")
CRON_SECRET: str = _require("CRON_SECRET")
APP_URL: str = os.environ.get("APP_URL", "http://localhost:8000")
# Used to sign dashboard session cookies. Falls back to CRON_SECRET if unset
# so existing deploys keep working, but a dedicated secret is recommended.
SESSION_SECRET: str = os.environ.get("SESSION_SECRET") or CRON_SECRET
# Optional: disable the LLM "insight" line in summaries to conserve rate limits.
SUMMARY_INSIGHT_ENABLED: bool = os.environ.get("SUMMARY_INSIGHT_ENABLED", "false").lower() == "true"
