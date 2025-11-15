import os
import json
import logging
import re
import sys
import argparse
import time
import datetime
import urllib.parse
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from email.message import EmailMessage
import smtplib

from email_validator import validate_email, EmailNotValidError

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    Text,
    Boolean,
    DateTime,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from ca_priority import apply_ca_priority, is_california_location


# -------------------------
# Environment / configuration
# -------------------------

load_dotenv()

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("leadfactory")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///leadfactory.db")

QUICKSCRAPER_ACCESS_TOKEN = os.getenv("QUICKSCRAPER_ACCESS_TOKEN", "").strip()
QUICKSCRAPER_EMAIL_PARSER_ID = os.getenv("QUICKSCRAPER_EMAIL_PARSER_ID", "").strip()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-7-sonnet-20250219").strip()

LEAD_SOURCES_JSON = os.getenv("LEAD_SOURCES_JSON", "[]")

SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "").strip()
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "Alex from Emigre.eu").strip()
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

MIN_INTENT_SCORE = float(os.getenv("MIN_INTENT_SCORE", "0.7"))
DAILY_OUTREACH_LIMIT = int(os.getenv("DAILY_OUTREACH_LIMIT", "40"))
TARGET_DAILY_BOOKINGS = int(os.getenv("TARGET_DAILY_BOOKINGS", "4"))

BOOKING_LINK = os.getenv("BOOKING_LINK", "").strip()


# -------------------------
# Database models
# -------------------------

Base = declarative_base()


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True, index=True)
    location = Column(String(255), nullable=True)
    platform = Column(String(50), nullable=True)
    profile_url = Column(String(512), nullable=True, index=True)
    source_url = Column(String(512), nullable=True)
    context = Column(Text, nullable=True)
    intent_summary = Column(Text, nullable=True)
    intent_score = Column(Float, nullable=True)
    priority_score = Column(Float, nullable=True, index=True)  # Score after CA boost
    is_ca_priority = Column(Boolean, default=False, index=True)  # CA priority flag
    tags = Column(Text, nullable=True)
    contacted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_contacted_at = Column(DateTime, nullable=True)


class OutreachLog(Base):
    __tablename__ = "outreach_logs"

    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, index=True)
    channel = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


# -------------------------
# Data classes
# -------------------------

@dataclass
class RawPage:
    platform: str
    url: str
    text: str


@dataclass
class LeadCandidate:
    name: Optional[str]
    location: Optional[str]
    email: Optional[str]
    platform: str
    profile_url: Optional[str]
    source_url: str
    context: str
    timeframe: Optional[str]
    move_reason: Optional[str]
    suitability: Optional[float]


# -------------------------
# QuickScraper client
# -------------------------

class QuickScraperClient:
    def __init__(self, access_token: str) -> None:
        if not access_token:
            raise ValueError("QUICKSCRAPER_ACCESS_TOKEN is not set.")
        self.access_token = access_token
        self.base_url = "https://api.quickscraper.co/parse"

    def _build_url(
        self,
        target_url: str,
        parser_subscription_id: Optional[str] = None,
    ) -> str:
        params = {
            "access_token": self.access_token,
            "url": target_url,
        }
        if parser_subscription_id:
            params["parserSubscriptionId"] = parser_subscription_id
        query = urllib.parse.urlencode(params, safe=":/?=&")
        return f"{self.base_url}?{query}"

    def fetch_html(
        self,
        target_url: str,
        parser_subscription_id: Optional[str] = None,
        timeout: int = 60,
    ) -> str:
        full_url = self._build_url(target_url, parser_subscription_id)
        logger.debug(f"QuickScraper GET {full_url}")
        resp = requests.get(full_url, timeout=timeout)
        resp.raise_for_status()
        return resp.text

    def fetch_json(
        self,
        target_url: str,
        parser_subscription_id: Optional[str] = None,
        timeout: int = 60,
    ) -> Any:
        text = self.fetch_html(target_url, parser_subscription_id, timeout)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning("QuickScraper JSON parse failed; returning raw text.")
            return text


# -------------------------
# Claude / Anthropic client
# -------------------------

class ClaudeClient:
    def __init__(self, api_key: str, model: str, max_tokens: int = 1024) -> None:
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set.")
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.base_url = "https://api.anthropic.com/v1/messages"

    def _request(self, system_prompt: str, user_prompt: str) -> str:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_prompt},
            ],
        }
        resp = requests.post(self.base_url, headers=headers, json=payload, timeout=90)
        resp.raise_for_status()
        data = resp.json()
        content = data.get("content", [])
        texts = [c.get("text", "") for c in content if c.get("type") == "text"]
        if not texts:
            return ""
        return texts[0]

    def complete_text(self, system_prompt: str, user_prompt: str) -> str:
        return self._request(system_prompt, user_prompt)

    def complete_json(self, system_prompt: str, user_prompt: str) -> Any:
        raw = self._request(system_prompt, user_prompt)
        raw_stripped = raw.strip()
        # Try to locate JSON block in the response
        first_brace = raw_stripped.find("[")
        if first_brace == -1:
            first_brace = raw_stripped.find("{")
        if first_brace == -1:
            raise ValueError(f"Claude response does not contain JSON: {raw_stripped}")
        json_part = raw_stripped[first_brace:]
        try:
            return json.loads(json_part)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Claude: {e} | text={json_part}")
            raise


# -------------------------
# Helper utilities
# -------------------------

EMAIL_REGEX = re.compile(
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", re.IGNORECASE
)


def extract_emails_from_text(text: str) -> List[str]:
    found = re.findall(EMAIL_REGEX, text or "")
    unique = []
    for e in found:
        normalized = e.strip().strip(".,;:()>\"'")
        if normalized and normalized not in unique:
            unique.append(normalized)
    return unique


def is_probable_california_location(location: Optional[str]) -> bool:
    if not location:
        return False
    loc_lower = location.lower()
    california_markers = [
        "california",
        "ca, usa",
        "los angeles",
        "san francisco",
        "bay area",
        "san diego",
        "sacramento",
        "orange county",
        "silicon valley",
    ]
    return any(marker in loc_lower for marker in california_markers)


def safe_validate_email(email: str) -> Optional[str]:
    try:
        v = validate_email(email, check_deliverability=False)
        return v.email
    except EmailNotValidError:
        return None


# -------------------------
# Agents
# -------------------------

class DiscoveryAgent:
    def __init__(self, qs: QuickScraperClient, lead_sources: List[Dict[str, Any]]) -> None:
        self.qs = qs
        self.lead_sources = lead_sources

    def run(self) -> List[RawPage]:
        pages: List[RawPage] = []
        for src in self.lead_sources:
            url = src.get("url")
            platform = src.get("platform", "unknown")
            if not url:
                continue
            try:
                logger.info(f"DiscoveryAgent: fetching {platform} {url}")
                html = self.qs.fetch_html(url)
                soup = BeautifulSoup(html, "html.parser")
                text = soup.get_text(separator="\n")
                pages.append(RawPage(platform=platform, url=url, text=text))
                time.sleep(2)  # polite delay
            except Exception as e:
                logger.error(f"DiscoveryAgent: error fetching {url}: {e}")
        logger.info(f"DiscoveryAgent: fetched {len(pages)} pages.")
        return pages


class ExtractionAgent:
    def __init__(self, claude: ClaudeClient) -> None:
        self.claude = claude

    def run(self, pages: List[RawPage]) -> List[LeadCandidate]:
        candidates: List[LeadCandidate] = []
        if not pages:
            return candidates

        system_prompt = (
            "You are a lead extraction agent for an EU immigration advisory.\n"
            "You read scraped text from online communities and identify people who:\n"
            "1) Live in California or clearly have ties to California, and\n"
            "2) Explicitly talk about wanting to move out of the USA (emigrate, retire abroad, move overseas, etc.).\n"
            "The goal is to invite them to a call about moving to Madeira (Portugal) and EU residency/migration options.\n\n"
            "You MUST respond with pure JSON, no commentary."
        )

        for page in pages:
            user_prompt = (
                "Extract up to 20 high-intent leads from the following text.\n"
                "For EACH lead, output an object with the keys:\n"
                "  name: string or null\n"
                "  location: string or null (include city + state if possible)\n"
                "  email: string or null (only if explicitly present in the text)\n"
                "  platform: string (e.g. 'reddit', 'facebook', 'forum')\n"
                "  profile_url: string or null if the text shows a profile or handle URL\n"
                "  source_url: string (the URL we scraped from)\n"
                "  context: short snippet (1-3 sentences) quoting/paraphrasing what they said about leaving the USA\n"
                "  timeframe: short phrase like 'within 1 year', '1-3 years', 'unsure', 'just exploring'\n"
                "  move_reason: short phrase about why they want to leave (e.g. 'cost of living', 'politics', 'quality of life', 'retirement')\n"
                "  suitability: float between 0 and 1 where 1 means extremely strong fit for Madeira/EU relocation (retirement, remote worker, property buyer etc.).\n\n"
                "Only include leads that clearly match BOTH criteria: California + wants to leave the USA.\n"
                "Return a JSON array of objects.\n\n"
                f"platform: {page.platform}\n"
                f"source_url: {page.url}\n\n"
                f"TEXT:\n{page.text[:18000]}"
            )
            try:
                result = self.claude.complete_json(system_prompt, user_prompt)
            except Exception as e:
                logger.error(f"ExtractionAgent: Claude error on {page.url}: {e}")
                continue

            if isinstance(result, dict):
                # Sometimes models wrap into {"leads": [...]}
                if "leads" in result and isinstance(result["leads"], list):
                    lead_list = result["leads"]
                else:
                    logger.warning("ExtractionAgent: unexpected dict JSON, skipping.")
                    continue
            elif isinstance(result, list):
                lead_list = result
            else:
                logger.warning("ExtractionAgent: JSON was not list or dict, skipping.")
                continue

            for raw in lead_list:
                try:
                    candidate = LeadCandidate(
                        name=raw.get("name"),
                        location=raw.get("location"),
                        email=raw.get("email"),
                        platform=raw.get("platform") or page.platform,
                        profile_url=raw.get("profile_url"),
                        source_url=raw.get("source_url") or page.url,
                        context=raw.get("context") or "",
                        timeframe=raw.get("timeframe"),
                        move_reason=raw.get("move_reason"),
                        suitability=float(raw.get("suitability"))
                        if raw.get("suitability") is not None
                        else None,
                    )
                    candidates.append(candidate)
                except Exception as e:
                    logger.error(f"ExtractionAgent: error building candidate: {e}")

        logger.info(f"ExtractionAgent: extracted {len(candidates)} lead candidates.")
        return candidates


class PersistenceAgent:
    def __init__(self, db: Session) -> None:
        self.db = db

    def upsert_leads(self, candidates: List[LeadCandidate]) -> int:
        created = 0
        for c in candidates:
            email_normalized = safe_validate_email(c.email) if c.email else None

            existing = None
            if email_normalized:
                existing = (
                    self.db.query(Lead)
                    .filter(Lead.email == email_normalized)
                    .one_or_none()
                )

            if existing is None and c.profile_url:
                existing = (
                    self.db.query(Lead)
                    .filter(Lead.profile_url == c.profile_url)
                    .one_or_none()
                )

            if existing:
                # Update basic fields but do not overwrite existing intent_score/contacted
                if not existing.location and c.location:
                    existing.location = c.location
                if not existing.profile_url and c.profile_url:
                    existing.profile_url = c.profile_url
                if not existing.context and c.context:
                    existing.context = c.context
                if not existing.source_url and c.source_url:
                    existing.source_url = c.source_url
                self.db.add(existing)
                continue

            lead = Lead(
                name=c.name,
                email=email_normalized,
                location=c.location,
                platform=c.platform,
                profile_url=c.profile_url,
                source_url=c.source_url,
                context=c.context,
                intent_summary=None,
                intent_score=c.suitability,
                tags=None,
                contacted=False,
            )
            self.db.add(lead)
            created += 1

        self.db.commit()
        logger.info(f"PersistenceAgent: created {created} new leads.")
        return created


class EnrichmentAgent:
    def __init__(self, qs: QuickScraperClient) -> None:
        self.qs = qs

    def _enrich_single_lead(self, lead: Lead, db: Session) -> None:
        if lead.email:
            return

        # Strategy:
        # 1. If profile_url present, scrape that (often profile pages show email).
        # 2. As fallback, search by name + 'California' and scrape first page.
        html_combined = ""

        if lead.profile_url:
            try:
                html = self.qs.fetch_html(lead.profile_url)
                html_combined += html
                time.sleep(2)
            except Exception as e:
                logger.error(f"EnrichmentAgent: error scraping profile {lead.profile_url}: {e}")

        if not html_combined and lead.name:
            query = f'"{lead.name}" "California" email contact'
            search_url = (
                "https://www.google.com/search?q="
                + urllib.parse.quote_plus(query)
            )
            try:
                html = self.qs.fetch_html(search_url)
                html_combined += html
                time.sleep(2)
            except Exception as e:
                logger.error(f"EnrichmentAgent: error scraping search for {lead.name}: {e}")

        if not html_combined:
            return

        emails = extract_emails_from_text(html_combined)
        for e in emails:
            valid = safe_validate_email(e)
            if not valid:
                continue
            lead.email = valid
            db.add(lead)
            db.commit()
            logger.info(f"EnrichmentAgent: found email {valid} for lead {lead.id}")
            return

    def run(self, db: Session, limit: int = 50) -> int:
        leads_to_enrich = (
            db.query(Lead)
            .filter(Lead.email.is_(None))
            .order_by(Lead.created_at.desc())
            .limit(limit)
            .all()
        )
        if not leads_to_enrich:
            logger.info("EnrichmentAgent: no leads to enrich.")
            return 0

        updated = 0
        for lead in leads_to_enrich:
            self._enrich_single_lead(lead, db)
            if lead.email:
                updated += 1
        logger.info(f"EnrichmentAgent: enriched {updated} leads with emails.")
        return updated


class QualificationAgent:
    def __init__(self, claude: ClaudeClient) -> None:
        self.claude = claude

    def _score_lead(self, lead: Lead) -> Optional[Dict[str, Any]]:
        system_prompt = (
            "You are a strict lead qualification agent for an EU immigration advisory "
            "specialised in Madeira (Portugal) residency and property-based relocation.\n"
            "You score leads on how suitable they are for a consult call about moving "
            "from California to Madeira/EU.\n"
            "Respond with pure JSON, no explanations."
        )

        user_prompt = (
            "You are given a single lead with these fields:\n"
            f"name: {lead.name}\n"
            f"location: {lead.location}\n"
            f"context: {lead.context}\n\n"
            "Decide:\n"
            "1. Is this person clearly in California or strongly tied to California?\n"
            "2. Do they clearly want to leave the USA / move abroad?\n"
            "3. Are they a good fit for EU/Madeira relocation (remote worker, retiree, property buyer, business owner, etc.)?\n\n"
            "Return a JSON object with:\n"
            "{\n"
            '  "is_california": true/false,\n'
            '  "wants_to_leave_usa": true/false,\n'
            '  "suitability_score": number between 0 and 1,\n'
            '  "intent_summary": short string summary,\n'
            '  "tags": [list of short tags]\n'
            "}\n"
        )

        try:
            data = self.claude.complete_json(system_prompt, user_prompt)
            if isinstance(data, dict):
                return data
        except Exception as e:
            logger.error(f"QualificationAgent: Claude error for lead {lead.id}: {e}")
        return None

    def run(self, db: Session, batch_size: int = 50) -> int:
        leads = (
            db.query(Lead)
            .filter(Lead.intent_score.is_(None))
            .order_by(Lead.created_at.desc())
            .limit(batch_size)
            .all()
        )
        if not leads:
            logger.info("QualificationAgent: no leads to score.")
            return 0

        updated = 0
        for lead in leads:
            payload = self._score_lead(lead)
            if not payload:
                continue

            is_cal = bool(payload.get("is_california"))
            wants_out = bool(payload.get("wants_to_leave_usa"))
            base_score = payload.get("suitability_score")
            intent_summary = payload.get("intent_summary")
            tags = payload.get("tags")

            if base_score is None:
                continue

            # Convert 0-1 score to 0-100 scale for consistency
            base_score_scaled = float(base_score) * 100

            # If clearly not from CA or not wanting to leave USA, downgrade base score
            if not is_cal or not wants_out:
                base_score_scaled = base_score_scaled * 0.2

            # Apply CA priority boost to get priority_score
            priority_score, is_ca_priority = apply_ca_priority(
                base_score=base_score_scaled,
                location=lead.location,
                ca_boost=2.0
            )

            # Update lead with both scores
            lead.intent_score = base_score_scaled
            lead.priority_score = priority_score
            lead.is_ca_priority = is_ca_priority

            if intent_summary:
                lead.intent_summary = intent_summary
            if tags is not None:
                lead.tags = json.dumps(tags)

            db.add(lead)
            updated += 1
            logger.info(f"Lead {lead.id}: base={base_score_scaled:.2f}, priority={priority_score:.2f}, CA={is_ca_priority}")

        db.commit()
        logger.info(f"QualificationAgent: updated {updated} leads with scores.")
        return updated


class EmailOutreachAgent:
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_username: str,
        smtp_password: str,
        from_email: str,
        from_name: str,
        use_tls: bool,
        min_intent_score: float,
        daily_limit: int,
        booking_link: str,
    ) -> None:
        if not smtp_host or not from_email:
            raise ValueError("SMTP configuration is incomplete.")
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.from_email = from_email
        self.from_name = from_name
        self.use_tls = use_tls
        self.min_intent_score = min_intent_score
        self.daily_limit = daily_limit
        self.booking_link = booking_link

    def _build_message(self, lead: Lead) -> EmailMessage:
        subject = "Exploring your move from California to Madeira / EU"
        greeting_name = lead.name or "there"
        context_snippet = (lead.context or "").strip()
        if len(context_snippet) > 400:
            context_snippet = context_snippet[:400] + "..."

        body = (
            f"Hi {greeting_name},\n\n"
            "I saw your recent post about wanting to move out of the USA from California, "
            "and thought it might be helpful to share a very specific path that a lot of "
            "Californians are taking right now.\n\n"
            "We specialise in helping people relocate to Madeira (a Portuguese island with "
            "warm weather, relatively low cost of living, and EU residency options) through "
            "property purchases and other legal pathways via Emigre.eu.\n\n"
            "From what you wrote:\n"
            f"\"{context_snippet}\"\n\n"
            "…it sounds like you might be considering exactly the kind of move we work with every day.\n\n"
            "If you'd like to explore what this could look like for you, you can pick a time for a "
            "short, no-pressure video call here:\n"
            f"{self.booking_link}\n\n"
            "On the call we usually cover:\n"
            "- Whether Madeira / Portugal realistically fits your goals and budget\n"
            "- Rough timelines and steps for getting out of the US\n"
            "- Property / investment options that can support residency pathways\n\n"
            "If this isn't relevant, or you'd rather not hear from me again, just reply with "
            ""no thanks" and I'll remove you from future outreach.\n\n"
            "Best regards,\n"
            f"{self.from_name}\n"
            "Emigre.eu\n"
        )

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = f"{self.from_name} <{self.from_email}>"
        msg["To"] = lead.email
        msg.set_content(body)
        return msg

    def _send_email(self, msg: EmailMessage) -> None:
        with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
            if self.use_tls:
                server.starttls()
            if self.smtp_username and self.smtp_password:
                server.login(self.smtp_username, self.smtp_password)
            server.send_message(msg)

    def run(self, db: Session) -> int:
        today = datetime.date.today()
        start_of_day = datetime.datetime.combine(today, datetime.time.min)
        end_of_day = datetime.datetime.combine(today, datetime.time.max)

        sent_today = (
            db.query(OutreachLog)
            .filter(
                OutreachLog.created_at >= start_of_day,
                OutreachLog.created_at <= end_of_day,
            )
            .count()
        )

        remaining = max(self.daily_limit - sent_today, 0)
        if remaining <= 0:
            logger.info("EmailOutreachAgent: daily outreach limit already reached.")
            return 0

        leads = (
            db.query(Lead)
            .filter(
                Lead.priority_score.isnot(None),
                Lead.intent_score >= self.min_intent_score,
                Lead.email.isnot(None),
                Lead.contacted.is_(False),
            )
            .order_by(Lead.priority_score.desc(), Lead.created_at.asc())  # Sort by priority_score to prioritize CA leads
            .limit(remaining)
            .all()
        )

        if not leads:
            logger.info("EmailOutreachAgent: no qualified leads to contact.")
            return 0

        count = 0
        for lead in leads:
            try:
                msg = self._build_message(lead)
                logger.info(f"EmailOutreachAgent: sending email to {lead.email}")
                self._send_email(msg)
                lead.contacted = True
                lead.last_contacted_at = datetime.datetime.utcnow()
                db.add(lead)
                log = OutreachLog(
                    lead_id=lead.id,
                    channel="email",
                    status="sent",
                    note="",
                )
                db.add(log)
                db.commit()
                count += 1
                time.sleep(1)
            except Exception as e:
                logger.error(f"EmailOutreachAgent: failed to email lead {lead.id}: {e}")
                log = OutreachLog(
                    lead_id=lead.id,
                    channel="email",
                    status="failed",
                    note=str(e),
                )
                db.add(log)
                db.commit()

        logger.info(f"EmailOutreachAgent: sent {count} emails this run.")
        return count


# -------------------------
# Orchestration / pipeline
# -------------------------

def load_lead_sources() -> List[Dict[str, Any]]:
    try:
        data = json.loads(LEAD_SOURCES_JSON)
        if isinstance(data, list):
            sources: List[Dict[str, Any]] = []
            for item in data:
                if isinstance(item, str):
                    sources.append({"platform": "unknown", "url": item})
                elif isinstance(item, dict):
                    sources.append(item)
            return sources
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LEAD_SOURCES_JSON: {e}")
    return []


def run_daily_pipeline() -> None:
    logger.info("=== LeadFactory California daily pipeline start ===")

    if not QUICKSCRAPER_ACCESS_TOKEN:
        logger.error("QUICKSCRAPER_ACCESS_TOKEN is missing, aborting.")
        return
    if not ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY is missing, aborting.")
        return
    if not BOOKING_LINK:
        logger.warning("BOOKING_LINK is not set; outreach emails will not contain a scheduling link.")

    qs_client = QuickScraperClient(QUICKSCRAPER_ACCESS_TOKEN)
    claude_client = ClaudeClient(ANTHROPIC_API_KEY, ANTHROPIC_MODEL)

    lead_sources = load_lead_sources()
    if not lead_sources:
        logger.warning("No lead sources configured; nothing to scrape.")
        return

    db = SessionLocal()

    try:
        # 1) Discover raw pages
        discovery = DiscoveryAgent(qs_client, lead_sources)
        raw_pages = discovery.run()

        # 2) Extract candidates via Claude
        extractor = ExtractionAgent(claude_client)
        candidates = extractor.run(raw_pages)

        # 3) Persist / dedupe
        persistence = PersistenceAgent(db)
        created_count = persistence.upsert_leads(candidates)

        # 4) Enrich missing emails
        enrichment = EnrichmentAgent(qs_client)
        enrichment.run(db, limit=50)

        # 5) Qualify / score
        qualifier = QualificationAgent(claude_client)
        qualifier.run(db, batch_size=50)

        # 6) Outreach
        outreach = EmailOutreachAgent(
            smtp_host=SMTP_HOST,
            smtp_port=SMTP_PORT,
            smtp_username=SMTP_USERNAME,
            smtp_password=SMTP_PASSWORD,
            from_email=SMTP_FROM_EMAIL,
            from_name=SMTP_FROM_NAME,
            use_tls=SMTP_USE_TLS,
            min_intent_score=MIN_INTENT_SCORE,
            daily_limit=DAILY_OUTREACH_LIMIT,
            booking_link=BOOKING_LINK,
        )
        sent = outreach.run(db)

        logger.info(
            f"Pipeline complete. New leads: {created_count}, emails sent: {sent}, "
            f"target daily bookings: {TARGET_DAILY_BOOKINGS}."
        )
    finally:
        db.close()
        logger.info("=== LeadFactory California daily pipeline end ===")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="LeadFactory California – automated lead generation pipeline."
    )
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Run the pipeline once and exit.",
    )
    args = parser.parse_args()

    init_db()

    if args.run_once:
        run_daily_pipeline()
    else:
        # Simple loop: run once per day at startup; you can replace with proper scheduler / cron.
        run_daily_pipeline()


if __name__ == "__main__":
    main()
