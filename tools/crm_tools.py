"""
CRM tools for managing leads, outreach, and analytics.
These functions wrap database operations for agent use.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy import and_, or_, func

from database import get_db
from database.models import (
    Lead, OutreachLog, Response, Meeting, Note,
    Source, AnalyticsSnapshot,
    LeadStage, OutreachChannel, OutreachStatus, ResponseSentiment
)


# ============================================================================
# LEAD MANAGEMENT
# ============================================================================

def create_lead(
    email: Optional[str] = None,
    reddit_username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Create a new lead in the CRM.

    Args:
        email: Email address (if known)
        reddit_username: Reddit username (if known)
        first_name: First name
        last_name: Last name
        **kwargs: Additional fields (city, state, source_url, etc.)

    Returns:
        Dict with lead data including ID
    """
    with get_db() as db:
        # Check for existing lead
        if email:
            existing = db.query(Lead).filter(Lead.email == email).first()
            if existing:
                return {"success": False, "error": "Lead already exists", "lead_id": existing.id}

        if reddit_username:
            existing = db.query(Lead).filter(Lead.reddit_username == reddit_username).first()
            if existing and not email:  # If we found them by reddit and don't have email
                return {"success": False, "error": "Lead already exists", "lead_id": existing.id}

        lead = Lead(
            email=email,
            reddit_username=reddit_username,
            first_name=first_name,
            last_name=last_name,
            **kwargs
        )
        db.add(lead)
        db.flush()

        return {
            "success": True,
            "lead_id": lead.id,
            "lead": lead.to_dict()
        }


def get_lead(lead_id: int) -> Optional[Dict[str, Any]]:
    """Get a lead by ID."""
    with get_db() as db:
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            return None
        return lead.to_dict()


def update_lead(lead_id: int, **updates) -> Dict[str, Any]:
    """
    Update lead fields.

    Args:
        lead_id: Lead ID
        **updates: Fields to update

    Returns:
        Updated lead data
    """
    with get_db() as db:
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            return {"success": False, "error": "Lead not found"}

        for key, value in updates.items():
            if hasattr(lead, key):
                setattr(lead, key, value)

        lead.updated_at = datetime.now(timezone.utc)
        db.flush()

        return {
            "success": True,
            "lead": lead.to_dict()
        }


def search_leads(filters: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
    """
    Search leads with flexible filters.

    Args:
        filters: Dict of filter criteria (e.g., {"stage": "qualified", "is_californian": True})
        limit: Max results to return

    Returns:
        List of lead dicts
    """
    with get_db() as db:
        query = db.query(Lead)

        # Apply filters
        for key, value in filters.items():
            if hasattr(Lead, key):
                query = query.filter(getattr(Lead, key) == value)

        leads = query.limit(limit).all()
        return [lead.to_dict() for lead in leads]


def get_leads_by_stage(stage: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Get all leads at a specific stage."""
    with get_db() as db:
        leads = db.query(Lead).filter(Lead.stage == stage).limit(limit).all()
        return [lead.to_dict() for lead in leads]


def update_lead_stage(lead_id: int, new_stage: str, notes: Optional[str] = None) -> Dict[str, Any]:
    """Update lead stage and record the change."""
    with get_db() as db:
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            return {"success": False, "error": "Lead not found"}

        old_stage = lead.stage
        lead.stage = LeadStage(new_stage)
        lead.stage_changed_at = datetime.now(timezone.utc)

        if notes:
            note = Note(
                lead_id=lead_id,
                note_text=f"Stage changed: {old_stage} → {new_stage}. {notes}",
                created_by="system",
                note_type="stage_change"
            )
            db.add(note)

        return {"success": True, "old_stage": old_stage.value, "new_stage": new_stage}


def update_lead_score(lead_id: int, score: float, qualification_notes: Optional[str] = None) -> Dict[str, Any]:
    """Update lead score and qualification status."""
    from config.settings import settings

    with get_db() as db:
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            return {"success": False, "error": "Lead not found"}

        lead.score = score
        lead.is_qualified = score >= settings.min_lead_score

        if qualification_notes:
            lead.qualification_notes = qualification_notes

        # Auto-update stage based on qualification
        if lead.is_qualified and lead.stage == LeadStage.ENRICHED:
            lead.stage = LeadStage.QUALIFIED
            lead.stage_changed_at = datetime.now(timezone.utc)
        elif not lead.is_qualified and lead.stage not in [LeadStage.RAW, LeadStage.ENRICHED]:
            lead.stage = LeadStage.DISQUALIFIED
            lead.stage_changed_at = datetime.now(timezone.utc)

        return {
            "success": True,
            "score": score,
            "is_qualified": lead.is_qualified,
            "stage": lead.stage.value
        }


# ============================================================================
# OUTREACH MANAGEMENT
# ============================================================================

def log_outreach(
    lead_id: int,
    channel: str,
    message_body: str,
    subject: Optional[str] = None,
    template_id: Optional[str] = None,
    sequence_step: int = 1,
    **kwargs
) -> Dict[str, Any]:
    """
    Log an outreach attempt.

    Args:
        lead_id: Lead ID
        channel: Communication channel (email, linkedin, etc.)
        message_body: Message content
        subject: Email subject (if applicable)
        template_id: Template identifier for tracking
        sequence_step: Which step in the sequence (1=initial, 2=follow-up, etc.)
        **kwargs: Additional fields

    Returns:
        Outreach log record
    """
    with get_db() as db:
        outreach = OutreachLog(
            lead_id=lead_id,
            channel=OutreachChannel(channel),
            message_body=message_body,
            subject=subject,
            template_id=template_id,
            sequence_step=sequence_step,
            **kwargs
        )
        db.add(outreach)
        db.flush()

        return {
            "success": True,
            "outreach_id": outreach.id,
            "lead_id": lead_id,
            "channel": channel
        }


def update_outreach_status(
    outreach_id: int,
    status: str,
    **kwargs
) -> Dict[str, Any]:
    """Update outreach status (sent, delivered, opened, etc.)."""
    with get_db() as db:
        outreach = db.query(OutreachLog).filter(OutreachLog.id == outreach_id).first()
        if not outreach:
            return {"success": False, "error": "Outreach not found"}

        outreach.status = OutreachStatus(status)

        # Update timestamps based on status
        timestamp_map = {
            "sent": "sent_at",
            "delivered": "delivered_at",
            "opened": "opened_at",
            "clicked": "clicked_at",
            "replied": "replied_at",
        }

        if status in timestamp_map:
            setattr(outreach, timestamp_map[status], datetime.now(timezone.utc))

        # Apply any additional updates
        for key, value in kwargs.items():
            if hasattr(outreach, key):
                setattr(outreach, key, value)

        return {"success": True, "outreach_id": outreach_id, "status": status}


def get_outreach_history(lead_id: int) -> List[Dict[str, Any]]:
    """Get all outreach history for a lead."""
    with get_db() as db:
        outreaches = db.query(OutreachLog).filter(
            OutreachLog.lead_id == lead_id
        ).order_by(OutreachLog.created_at.desc()).all()

        return [{
            "id": o.id,
            "channel": o.channel.value,
            "status": o.status.value,
            "sequence_step": o.sequence_step,
            "sent_at": o.sent_at.isoformat() if o.sent_at else None,
            "template_id": o.template_id,
        } for o in outreaches]


# ============================================================================
# RESPONSE MANAGEMENT
# ============================================================================

def log_response(
    lead_id: int,
    channel: str,
    message_body: str,
    sentiment: Optional[str] = None,
    outreach_log_id: Optional[int] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Log an incoming response from a lead.

    Args:
        lead_id: Lead ID
        channel: Channel they replied on
        message_body: Their message
        sentiment: Classified sentiment (positive, neutral, questions, etc.)
        outreach_log_id: Which outreach they're replying to
        **kwargs: Additional fields (ai_summary, extracted_questions, etc.)

    Returns:
        Response record
    """
    with get_db() as db:
        response = Response(
            lead_id=lead_id,
            channel=OutreachChannel(channel),
            message_body=message_body,
            sentiment=ResponseSentiment(sentiment) if sentiment else None,
            outreach_log_id=outreach_log_id,
            is_positive=sentiment in ["positive", "questions"] if sentiment else None,
            **kwargs
        )
        db.add(response)
        db.flush()

        # Update lead stage
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if lead:
            if lead.stage == LeadStage.CONTACTED:
                lead.stage = LeadStage.RESPONDED
                lead.stage_changed_at = datetime.now(timezone.utc)

            if sentiment == "positive":
                lead.stage = LeadStage.INTERESTED
                lead.stage_changed_at = datetime.now(timezone.utc)

        return {
            "success": True,
            "response_id": response.id,
            "lead_id": lead_id,
            "sentiment": sentiment
        }


def get_pending_responses(limit: int = 50) -> List[Dict[str, Any]]:
    """Get responses that need agent reply."""
    with get_db() as db:
        responses = db.query(Response).filter(
            Response.agent_replied_at.is_(None),
            Response.sentiment.in_([ResponseSentiment.POSITIVE, ResponseSentiment.QUESTIONS])
        ).order_by(Response.created_at.asc()).limit(limit).all()

        return [{
            "id": r.id,
            "lead_id": r.lead_id,
            "message": r.message_body,
            "sentiment": r.sentiment.value,
            "questions": r.extracted_questions,
            "created_at": r.created_at.isoformat()
        } for r in responses]


# ============================================================================
# MEETING MANAGEMENT
# ============================================================================

def create_meeting(
    lead_id: int,
    scheduled_at: datetime,
    google_event_id: Optional[str] = None,
    google_meet_link: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """Create a meeting record."""
    with get_db() as db:
        meeting = Meeting(
            lead_id=lead_id,
            scheduled_at=scheduled_at,
            google_event_id=google_event_id,
            google_meet_link=google_meet_link,
            **kwargs
        )
        db.add(meeting)
        db.flush()

        # Update lead stage
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if lead:
            lead.stage = LeadStage.CALL_BOOKED
            lead.stage_changed_at = datetime.now(timezone.utc)

        return {
            "success": True,
            "meeting_id": meeting.id,
            "google_meet_link": google_meet_link,
            "scheduled_at": scheduled_at.isoformat()
        }


def get_todays_meetings() -> List[Dict[str, Any]]:
    """Get all meetings scheduled for today."""
    from datetime import date
    with get_db() as db:
        today = date.today()
        meetings = db.query(Meeting).filter(
            func.date(Meeting.scheduled_at) == today,
            Meeting.cancelled_at.is_(None)
        ).order_by(Meeting.scheduled_at).all()

        return [{
            "id": m.id,
            "lead_id": m.lead_id,
            "lead_name": m.lead.full_name,
            "scheduled_at": m.scheduled_at.isoformat(),
            "google_meet_link": m.google_meet_link,
            "is_confirmed": m.is_confirmed
        } for m in meetings]


# ============================================================================
# SOURCE MANAGEMENT
# ============================================================================

def create_or_update_source(
    platform: str,
    source_name: str,
    **kwargs
) -> Dict[str, Any]:
    """Create or update a lead source."""
    with get_db() as db:
        source = db.query(Source).filter(
            Source.platform == platform,
            Source.source_name == source_name
        ).first()

        if source:
            # Update existing
            for key, value in kwargs.items():
                if hasattr(source, key):
                    setattr(source, key, value)
        else:
            # Create new
            source = Source(
                platform=platform,
                source_name=source_name,
                **kwargs
            )
            db.add(source)

        db.flush()

        return {
            "success": True,
            "source_id": source.id,
            "platform": platform,
            "source_name": source_name
        }


def get_active_sources() -> List[Dict[str, Any]]:
    """Get all active lead sources."""
    with get_db() as db:
        sources = db.query(Source).filter(Source.is_active == True).all()

        return [{
            "id": s.id,
            "platform": s.platform,
            "source_name": s.source_name,
            "source_url": s.source_url,
            "keywords": s.search_keywords,
            "qualification_rate": s.qualification_rate,
            "booking_rate": s.booking_rate,
        } for s in sources]


def update_source_stats(source_id: int, **stats) -> Dict[str, Any]:
    """Update source performance statistics."""
    with get_db() as db:
        source = db.query(Source).filter(Source.id == source_id).first()
        if not source:
            return {"success": False, "error": "Source not found"}

        for key, value in stats.items():
            if hasattr(source, key):
                setattr(source, key, value)

        source.last_checked_at = datetime.now(timezone.utc)

        return {"success": True, "source_id": source_id}


# ============================================================================
# ANALYTICS
# ============================================================================

def get_pipeline_stats() -> Dict[str, Any]:
    """Get current funnel/pipeline statistics."""
    with get_db() as db:
        stats = {}

        # Count by stage
        for stage in LeadStage:
            count = db.query(Lead).filter(Lead.stage == stage).count()
            stats[f"stage_{stage.value}"] = count

        # Today's stats
        from datetime import date, timedelta
        today = date.today()
        today_start = datetime.combine(today, datetime.min.time())

        stats["calls_booked_today"] = db.query(Meeting).filter(
            func.date(Meeting.created_at) == today
        ).count()

        stats["outreach_sent_today"] = db.query(OutreachLog).filter(
            func.date(OutreachLog.sent_at) == today
        ).count()

        stats["responses_today"] = db.query(Response).filter(
            func.date(Response.created_at) == today
        ).count()

        # Qualified leads available for outreach
        stats["qualified_not_contacted"] = db.query(Lead).filter(
            Lead.is_qualified == True,
            Lead.stage == LeadStage.QUALIFIED
        ).count()

        return stats


def create_daily_snapshot(snapshot_date: Optional[datetime] = None) -> Dict[str, Any]:
    """Create analytics snapshot for a date."""
    from datetime import date
    if snapshot_date is None:
        snapshot_date = datetime.combine(date.today(), datetime.min.time())

    with get_db() as db:
        # Check if snapshot exists
        existing = db.query(AnalyticsSnapshot).filter(
            func.date(AnalyticsSnapshot.snapshot_date) == snapshot_date.date()
        ).first()

        if existing:
            return {"success": False, "error": "Snapshot already exists for this date"}

        # Calculate metrics for the day
        day_start = snapshot_date
        day_end = day_start + timedelta(days=1)

        snapshot = AnalyticsSnapshot(snapshot_date=snapshot_date)

        # Funnel counts (cumulative)
        snapshot.leads_raw = db.query(Lead).count()
        snapshot.leads_qualified = db.query(Lead).filter(Lead.is_qualified == True).count()

        # Daily activity
        snapshot.emails_sent = db.query(OutreachLog).filter(
            OutreachLog.channel == OutreachChannel.EMAIL,
            OutreachLog.sent_at >= day_start,
            OutreachLog.sent_at < day_end
        ).count()

        snapshot.calls_booked = db.query(Meeting).filter(
            Meeting.created_at >= day_start,
            Meeting.created_at < day_end
        ).count()

        snapshot.total_responses = db.query(Response).filter(
            Response.created_at >= day_start,
            Response.created_at < day_end
        ).count()

        snapshot.positive_responses = db.query(Response).filter(
            Response.created_at >= day_start,
            Response.created_at < day_end,
            Response.sentiment == ResponseSentiment.POSITIVE
        ).count()

        # Calculate rates
        total_sent = snapshot.emails_sent
        if total_sent > 0:
            snapshot.response_rate = (snapshot.total_responses / total_sent) * 100
            snapshot.booking_rate = (snapshot.calls_booked / total_sent) * 100

        db.add(snapshot)
        db.flush()

        return {
            "success": True,
            "snapshot_id": snapshot.id,
            "calls_booked": snapshot.calls_booked,
            "response_rate": snapshot.response_rate
        }
