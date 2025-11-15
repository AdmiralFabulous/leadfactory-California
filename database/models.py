"""
Database models for LeadFactory California CRM.
Uses SQLAlchemy ORM for database-agnostic operations.
"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    Text, ForeignKey, JSON, Enum as SQLEnum, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

Base = declarative_base()


# ============================================================================
# ENUMS
# ============================================================================

class LeadStage(str, enum.Enum):
    """Lead progression through the funnel."""
    RAW = "raw"                      # Just extracted, not enriched
    ENRICHED = "enriched"            # Has contact info
    QUALIFIED = "qualified"          # Scored and passed qualification
    CONTACTED = "contacted"          # First outreach sent
    RESPONDED = "responded"          # They replied
    INTERESTED = "interested"        # Positive response
    CALL_BOOKED = "call_booked"      # Meeting scheduled
    CALL_COMPLETED = "call_completed"  # Had the call
    CONVERTED = "converted"          # Became a client
    DISQUALIFIED = "disqualified"    # Doesn't meet criteria
    NOT_INTERESTED = "not_interested"  # Explicitly declined
    UNRESPONSIVE = "unresponsive"    # No response after sequence


class OutreachChannel(str, enum.Enum):
    """Communication channels."""
    EMAIL = "email"
    LINKEDIN = "linkedin"
    REDDIT_DM = "reddit_dm"
    TWITTER_DM = "twitter_dm"
    SMS = "sms"


class OutreachStatus(str, enum.Enum):
    """Status of an outreach attempt."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    REPLIED = "replied"
    BOUNCED = "bounced"
    FAILED = "failed"


class ResponseSentiment(str, enum.Enum):
    """Classification of lead responses."""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    QUESTIONS = "questions"
    NOT_INTERESTED = "not_interested"
    SPAM_COMPLAINT = "spam_complaint"


# ============================================================================
# MODELS
# ============================================================================

class Lead(Base):
    """Core lead/contact record."""
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Identity
    first_name = Column(String(100))
    last_name = Column(String(100))
    email = Column(String(255), unique=True, index=True)
    phone = Column(String(50))

    # Social profiles
    linkedin_url = Column(String(500))
    reddit_username = Column(String(100), index=True)
    twitter_handle = Column(String(100))

    # Location
    city = Column(String(100))
    state = Column(String(50), index=True)
    country = Column(String(50), default="USA")
    timezone = Column(String(50))

    # Professional info
    job_title = Column(String(200))
    company = Column(String(200))
    industry = Column(String(100))
    estimated_income_bracket = Column(String(50))  # e.g., "100k-200k"

    # Lead intelligence
    source_platform = Column(String(50), index=True)  # reddit, linkedin, etc.
    source_url = Column(Text)  # URL where we found them
    original_post_snippet = Column(Text)  # Their post/comment that flagged them
    pain_points = Column(JSON)  # ["taxes", "cost_of_living", "safety"]
    interests = Column(JSON)  # ["portugal", "digital_nomad", "early_retirement"]

    # Scoring & qualification
    score = Column(Float, default=0.0, index=True)
    is_qualified = Column(Boolean, default=False, index=True)
    qualification_notes = Column(Text)
    disqualification_reason = Column(Text)

    # Stage tracking
    stage = Column(SQLEnum(LeadStage), default=LeadStage.RAW, index=True)
    stage_changed_at = Column(DateTime)

    # Flags
    is_californian = Column(Boolean, default=False, index=True)
    expressed_leaving_intent = Column(Boolean, default=False, index=True)
    likely_property_buyer = Column(Boolean, default=False)
    do_not_contact = Column(Boolean, default=False, index=True)
    opted_out = Column(Boolean, default=False, index=True)

    # Preferred contact
    preferred_channel = Column(SQLEnum(OutreachChannel))
    best_time_to_contact = Column(String(100))  # e.g., "evenings PST"

    # Relationships
    outreach_history = relationship("OutreachLog", back_populates="lead", cascade="all, delete-orphan")
    responses = relationship("Response", back_populates="lead", cascade="all, delete-orphan")
    meetings = relationship("Meeting", back_populates="lead", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="lead", cascade="all, delete-orphan")

    # Indexes for common queries
    __table_args__ = (
        Index('idx_qualified_stage', 'is_qualified', 'stage'),
        Index('idx_californian_intent', 'is_californian', 'expressed_leaving_intent'),
        Index('idx_score_stage', 'score', 'stage'),
    )

    def __repr__(self):
        return f"<Lead {self.id}: {self.first_name} {self.last_name} ({self.stage})>"

    @property
    def full_name(self):
        """Get full name."""
        parts = [p for p in [self.first_name, self.last_name] if p]
        return " ".join(parts) if parts else self.email or self.reddit_username

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.full_name,
            "email": self.email,
            "city": self.city,
            "state": self.state,
            "score": self.score,
            "stage": self.stage.value if self.stage else None,
            "is_qualified": self.is_qualified,
            "source": self.source_platform,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class OutreachLog(Base):
    """Log of all outreach attempts."""
    __tablename__ = "outreach_logs"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, index=True)
    lead = relationship("Lead", back_populates="outreach_history")

    # Outreach details
    channel = Column(SQLEnum(OutreachChannel), nullable=False)
    status = Column(SQLEnum(OutreachStatus), default=OutreachStatus.PENDING)

    # Message content
    subject = Column(String(500))  # For email
    message_body = Column(Text, nullable=False)
    template_id = Column(String(100))  # Which template/variant was used
    personalization_data = Column(JSON)  # Variables used in personalization

    # Sequence tracking
    sequence_step = Column(Integer, default=1)  # 1 = initial, 2 = first follow-up, etc.
    parent_outreach_id = Column(Integer, ForeignKey("outreach_logs.id"))  # If follow-up

    # Delivery tracking
    sent_at = Column(DateTime)
    delivered_at = Column(DateTime)
    opened_at = Column(DateTime)
    clicked_at = Column(DateTime)
    replied_at = Column(DateTime)

    # Metadata
    external_message_id = Column(String(255))  # Email message ID, LinkedIn msg ID, etc.
    error_message = Column(Text)
    compliance_approved = Column(Boolean, default=False)
    compliance_notes = Column(Text)

    def __repr__(self):
        return f"<OutreachLog {self.id}: Lead {self.lead_id} via {self.channel} ({self.status})>"


class Response(Base):
    """Incoming responses from leads."""
    __tablename__ = "responses"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, index=True)
    lead = relationship("Lead", back_populates="responses")

    outreach_log_id = Column(Integer, ForeignKey("outreach_logs.id"))  # Which outreach they're replying to

    # Response details
    channel = Column(SQLEnum(OutreachChannel), nullable=False)
    message_body = Column(Text, nullable=False)
    external_message_id = Column(String(255))

    # Classification
    sentiment = Column(SQLEnum(ResponseSentiment), index=True)
    is_positive = Column(Boolean, index=True)
    has_questions = Column(Boolean, default=False)
    needs_human_review = Column(Boolean, default=False, index=True)

    # AI analysis
    ai_summary = Column(Text)  # What the lead said, summarized
    extracted_objections = Column(JSON)  # ["cost", "timing"]
    extracted_questions = Column(JSON)  # List of questions they asked
    next_action_suggested = Column(String(100))  # "book_call", "answer_questions", etc.

    # Response tracking
    agent_replied_at = Column(DateTime)
    agent_reply_id = Column(Integer, ForeignKey("outreach_logs.id"))

    def __repr__(self):
        return f"<Response {self.id}: Lead {self.lead_id} - {self.sentiment}>"


class Meeting(Base):
    """Scheduled and completed meetings."""
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, index=True)
    lead = relationship("Lead", back_populates="meetings")

    # Meeting details
    title = Column(String(255), default="Madeira Residency Consultation")
    scheduled_at = Column(DateTime, nullable=False, index=True)
    duration_minutes = Column(Integer, default=30)
    timezone = Column(String(50))

    # Google Calendar
    google_event_id = Column(String(255), unique=True)
    google_meet_link = Column(String(500))
    google_calendar_link = Column(String(500))

    # Status
    is_confirmed = Column(Boolean, default=False)
    is_completed = Column(Boolean, default=False, index=True)
    was_no_show = Column(Boolean, default=False)
    cancelled_at = Column(DateTime)
    cancellation_reason = Column(Text)

    # Outcome
    outcome_notes = Column(Text)
    converted_to_client = Column(Boolean, default=False)
    follow_up_required = Column(Boolean, default=False)
    next_steps = Column(Text)

    def __repr__(self):
        return f"<Meeting {self.id}: Lead {self.lead_id} at {self.scheduled_at}>"


class Note(Base):
    """Manual notes about leads."""
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, index=True)
    lead = relationship("Lead", back_populates="notes")

    note_text = Column(Text, nullable=False)
    created_by = Column(String(100))  # "system", "agent_name", or "human"
    note_type = Column(String(50))  # "qualification", "outreach", "call", "general"

    def __repr__(self):
        return f"<Note {self.id}: Lead {self.lead_id}>"


class Source(Base):
    """Lead sources and their performance."""
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Source identity
    platform = Column(String(50), index=True)  # reddit, linkedin, google
    source_name = Column(String(255), nullable=False)  # Subreddit name, group name, search query
    source_url = Column(String(500))
    source_type = Column(String(50))  # subreddit, facebook_group, linkedin_group, search_query

    # Configuration
    search_keywords = Column(JSON)  # Keywords to search for
    is_active = Column(Boolean, default=True, index=True)
    check_frequency_hours = Column(Integer, default=24)

    # Performance metrics
    total_leads_found = Column(Integer, default=0)
    total_qualified = Column(Integer, default=0)
    total_contacted = Column(Integer, default=0)
    total_responses = Column(Integer, default=0)
    total_calls_booked = Column(Integer, default=0)

    last_checked_at = Column(DateTime)
    last_lead_found_at = Column(DateTime)

    def __repr__(self):
        return f"<Source {self.id}: {self.platform}/{self.source_name}>"

    @property
    def qualification_rate(self):
        """Percentage of leads that qualify."""
        if self.total_leads_found == 0:
            return 0
        return (self.total_qualified / self.total_leads_found) * 100

    @property
    def booking_rate(self):
        """Percentage of contacted leads that book calls."""
        if self.total_contacted == 0:
            return 0
        return (self.total_calls_booked / self.total_contacted) * 100


class AnalyticsSnapshot(Base):
    """Daily analytics snapshots for tracking system performance."""
    __tablename__ = "analytics_snapshots"

    id = Column(Integer, primary_key=True)
    snapshot_date = Column(DateTime, nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Daily funnel metrics
    leads_raw = Column(Integer, default=0)
    leads_enriched = Column(Integer, default=0)
    leads_qualified = Column(Integer, default=0)
    leads_contacted = Column(Integer, default=0)
    leads_responded = Column(Integer, default=0)
    calls_booked = Column(Integer, default=0)
    calls_completed = Column(Integer, default=0)

    # Outreach volume
    emails_sent = Column(Integer, default=0)
    linkedin_messages_sent = Column(Integer, default=0)
    reddit_dms_sent = Column(Integer, default=0)

    # Response metrics
    total_responses = Column(Integer, default=0)
    positive_responses = Column(Integer, default=0)
    neutral_responses = Column(Integer, default=0)
    negative_responses = Column(Integer, default=0)

    # Conversion rates (calculated)
    response_rate = Column(Float, default=0.0)
    booking_rate = Column(Float, default=0.0)
    qualification_rate = Column(Float, default=0.0)

    # Performance by channel (JSON)
    channel_performance = Column(JSON)  # {"email": {...}, "linkedin": {...}}
    source_performance = Column(JSON)  # Performance by source
    template_performance = Column(JSON)  # A/B test results

    def __repr__(self):
        return f"<AnalyticsSnapshot {self.snapshot_date}: {self.calls_booked} calls>"


class TaskQueue(Base):
    """Task queue for agent work items."""
    __tablename__ = "task_queue"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Task details
    task_type = Column(String(100), nullable=False, index=True)  # FIND_LEADS, SEND_OUTREACH, etc.
    task_payload = Column(JSON)  # Task-specific data
    priority = Column(Integer, default=5, index=True)  # 1 = highest, 10 = lowest

    # Scheduling
    run_at = Column(DateTime, nullable=False, index=True)  # When to execute
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    failed_at = Column(DateTime)

    # Status
    status = Column(String(20), default="pending", index=True)  # pending, running, completed, failed
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    error_message = Column(Text)

    # Results
    result_data = Column(JSON)

    __table_args__ = (
        Index('idx_task_execution', 'status', 'run_at', 'priority'),
    )

    def __repr__(self):
        return f"<Task {self.id}: {self.task_type} ({self.status})>"
