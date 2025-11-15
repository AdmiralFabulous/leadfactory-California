"""
Configuration settings for LeadFactory California.
Loads from environment variables with validation.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, validator
from typing import List, Optional
import os
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )

    # ========================================================================
    # ANTHROPIC
    # ========================================================================
    anthropic_api_key: str = Field(..., description="Anthropic API key")
    anthropic_model: str = Field(
        default="claude-sonnet-4-5-20250929",
        description="Claude model to use"
    )

    # ========================================================================
    # GOOGLE APIs
    # ========================================================================
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    google_refresh_token: Optional[str] = None
    gmail_sender_email: Optional[str] = None
    gmail_sender_name: Optional[str] = "LeadFactory"
    google_calendar_id: str = "primary"
    meeting_duration_minutes: int = 30

    # ========================================================================
    # SOCIAL MEDIA APIs
    # ========================================================================
    reddit_client_id: Optional[str] = None
    reddit_client_secret: Optional[str] = None
    reddit_user_agent: str = "LeadFactoryBot/1.0"

    linkedin_access_token: Optional[str] = None
    linkedin_client_id: Optional[str] = None
    linkedin_client_secret: Optional[str] = None

    # ========================================================================
    # ENRICHMENT APIs
    # ========================================================================
    apollo_api_key: Optional[str] = None
    hunter_api_key: Optional[str] = None
    clearbit_api_key: Optional[str] = None

    # ========================================================================
    # SEARCH & SCRAPING
    # ========================================================================
    google_search_api_key: Optional[str] = None
    google_search_engine_id: Optional[str] = None
    serpapi_key: Optional[str] = None

    # ========================================================================
    # SYSTEM CONFIGURATION
    # ========================================================================
    daily_call_target: int = 4
    max_daily_outreach: int = 150
    min_lead_score: int = 60

    target_state: str = "California"
    target_cities: List[str] = Field(
        default=[
            "San Francisco", "Los Angeles", "San Diego",
            "San Jose", "Oakland", "Sacramento"
        ]
    )

    timezone: str = "America/Los_Angeles"

    # Database
    database_url: str = Field(
        default=f"sqlite:///{PROJECT_ROOT}/data/leadfactory.db"
    )
    redis_url: Optional[str] = None

    # ========================================================================
    # SCHEDULING
    # ========================================================================
    orchestrator_run_time: str = "07:00"
    response_check_interval_minutes: int = 60
    followup_day_1: int = 3
    followup_day_2: int = 7

    # ========================================================================
    # OUTREACH SETTINGS
    # ========================================================================
    email_rate_limit_per_hour: int = 50
    linkedin_rate_limit_per_hour: int = 20
    reddit_rate_limit_per_hour: int = 30

    personalization_level: str = "high"  # low, medium, high
    use_ab_testing: bool = True

    # ========================================================================
    # COMPLIANCE & SAFETY
    # ========================================================================
    compliance_review_enabled: bool = True
    compliance_min_confidence: float = 0.85
    include_optout_footer: bool = True
    spam_check_enabled: bool = True

    # ========================================================================
    # LOGGING & MONITORING
    # ========================================================================
    log_level: str = "INFO"
    log_file: str = Field(default=f"{PROJECT_ROOT}/data/logs/leadfactory.log")
    sentry_dsn: Optional[str] = None

    # ========================================================================
    # DASHBOARD
    # ========================================================================
    dashboard_host: str = "0.0.0.0"
    dashboard_port: int = 5000
    dashboard_secret_key: str = "change-this-in-production"

    # ========================================================================
    # DEVELOPMENT
    # ========================================================================
    dry_run: bool = False
    debug: bool = False
    test_mode: bool = False

    @validator('target_cities', pre=True)
    def parse_cities(cls, v):
        """Parse comma-separated cities string."""
        if isinstance(v, str):
            return [city.strip() for city in v.split(',')]
        return v

    @validator('database_url')
    def create_db_directory(cls, v):
        """Ensure database directory exists."""
        if v.startswith('sqlite'):
            db_path = v.replace('sqlite:///', '')
            db_dir = Path(db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)
        return v

    @validator('log_file')
    def create_log_directory(cls, v):
        """Ensure log directory exists."""
        log_dir = Path(v).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        return v

    @property
    def data_dir(self) -> Path:
        """Path to data directory."""
        path = PROJECT_ROOT / "data"
        path.mkdir(exist_ok=True)
        return path

    @property
    def chroma_db_path(self) -> Path:
        """Path to ChromaDB storage."""
        path = self.data_dir / "chroma_kb"
        path.mkdir(exist_ok=True)
        return str(path)

    def has_google_auth(self) -> bool:
        """Check if Google authentication is configured."""
        return all([
            self.google_client_id,
            self.google_client_secret,
            self.google_refresh_token
        ])

    def has_reddit_auth(self) -> bool:
        """Check if Reddit API is configured."""
        return all([
            self.reddit_client_id,
            self.reddit_client_secret
        ])

    def has_linkedin_auth(self) -> bool:
        """Check if LinkedIn API is configured."""
        return bool(self.linkedin_access_token)


# Global settings instance
settings = Settings()


# Scoring weights for lead qualification
SCORING_WEIGHTS = {
    "location_california": 30,
    "explicit_leaving_intent": 25,
    "high_income_proxy": 20,
    "recent_activity": 10,
    "detailed_post": 10,
    "professional_profile": 5,
}

# Disqualification flags
DISQUALIFICATION_FLAGS = {
    "student": -20,
    "mentions_broke": -25,
    "no_income": -30,
    "outside_california": -50,
    "no_leaving_intent": -40,
}

# Source definitions (updated by SourceDiscoveryAgent)
DEFAULT_SOURCES = {
    "reddit": {
        "subreddits": [
            "IWantOut",
            "expat",
            "AmerExit",
            "California",
            "bayarea",
            "LosAngeles",
            "SanDiego",
            "digitalnomad",
            "Fire",
            "fatFIRE",
        ],
        "keywords": [
            "leaving california",
            "leaving USA",
            "move to portugal",
            "california too expensive",
            "california taxes",
            "escape california",
        ],
    },
    "web_search": {
        "queries": [
            "californians moving to portugal",
            "leaving california for europe",
            "california expat portugal",
            "california golden visa",
            "retire in madeira from california",
        ]
    },
}

# Outreach message templates (basic - expanded by OutreachCopyAgent)
MESSAGE_TEMPLATES = {
    "email": {
        "subject_variants": [
            "California → Portugal pathway you might not know about",
            "Helping Californians explore Madeira residency options",
            "Quick question about your Portugal/expat plans",
        ],
        "opening_variants": [
            "saw_post_about_leaving",
            "fellow_californian",
            "tax_focused",
            "lifestyle_focused",
        ],
    },
}
