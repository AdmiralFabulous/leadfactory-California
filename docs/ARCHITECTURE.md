## System Architecture

LeadFactory California uses a **multi-agent architecture** where specialized AI agents collaborate to achieve the goal of booking 4+ qualified calls per day.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR AGENT                        │
│              (Daily planning & coordination)                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
┌─────────────┐  ┌──────────┐  ┌──────────────┐
│ ACQUISITION │  │ OUTREACH │  │  ANALYTICS   │
│   LAYER     │  │  LAYER   │  │    LAYER     │
└─────────────┘  └──────────┘  └──────────────┘
         │             │
         ▼             ▼
┌────────────────────────────────────────┐
│         LEAD DATABASE (CRM)             │
│    - Leads & contacts                   │
│    - Outreach history                   │
│    - Call bookings                      │
└────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────┐
│    EXTERNAL INTEGRATIONS                │
│  - Gmail API                            │
│  - Google Calendar API                  │
│  - Reddit API                           │
│  - Web search & scraping                │
└────────────────────────────────────────┘
```

## Core Components

### 1. Agent Layer

**13 Specialized Agents:**

**Coordination:**
- `OrchestratorAgent` - Plans daily work, ensures KPIs

**Acquisition:**
- `SourceDiscoveryAgent` - Finds lead sources
- `LeadExtractionAgent` - Extracts leads from sources
- `LeadEnrichmentAgent` - Enriches with contact info

**Qualification:**
- `LeadScoringAgent` - Scores and qualifies leads

**Knowledge:**
- `OfferKnowledgeAgent` - emigre.eu expert

**Outreach:**
- `OutreachCopyAgent` - Writes personalized messages
- `ComplianceAgent` - Ensures legal compliance
- `OutreachSequencerAgent` - Sends and schedules messages
- `ReplyTriageAgent` - Classifies responses
- `LeadConversationAgent` - Answers questions
- `BookingAgent` - Schedules calls

**Analytics:**
- `AnalyticsAgent` - Tracks performance, optimizes

### 2. Data Layer

**Database Schema (SQLite/PostgreSQL):**

- `leads` - Core lead records
- `outreach_logs` - All outbound messages
- `responses` - Incoming replies
- `meetings` - Scheduled calls
- `sources` - Lead source performance
- `analytics_snapshots` - Daily metrics
- `task_queue` - Scheduled agent tasks

**Knowledge Base (ChromaDB):**

- Vector store for emigre.eu content
- Semantic search for Q&A

### 3. Tools Layer

**CRM Tools:**
- Lead CRUD operations
- Outreach logging
- Response tracking
- Meeting management
- Analytics queries

**External Service Tools:**
- Gmail (send/receive emails)
- Google Calendar (create meetings)
- Reddit (search posts, send DMs)
- Web search & scraping
- Knowledge base search

**Task Queue:**
- Schedule asynchronous work
- Retry failed tasks
- Priority scheduling

### 4. Scheduler Layer

**APScheduler jobs:**

- **Daily (7:00 AM):** Orchestrator plans day
- **Hourly:** Check responses
- **Every 5 min:** Process task queue
- **Daily (11:59 PM):** Create analytics snapshot

## Data Flow

### New Lead Flow

```
1. SourceDiscoveryAgent → Maintains list of sources
2. LeadExtractionAgent → Finds people in sources
3. LeadEnrichmentAgent → Gets contact info
4. LeadScoringAgent → Scores lead (0-100)
5. If score >= 60 → Qualified
6. OutreachSequencerAgent → Sends personalized message
7. Follow-ups scheduled automatically (Day 3, Day 7)
8. ReplyTriageAgent → Monitors inbox
9. On positive response → BookingAgent
10. Call scheduled → Success!
```

### Daily Workflow

```
07:00 - OrchestratorAgent runs
        ├─ Checks: How many calls booked?
        ├─ Calculates: How many leads/outreach needed?
        └─ Enqueues tasks

07:10 - LeadExtractionAgent
        └─ Finds 100 raw leads from Reddit, forums

07:30 - LeadEnrichmentAgent
        └─ Enriches 100 → 30 have usable contact info

07:45 - LeadScoringAgent
        └─ Scores 30 → 15 qualify (score >= 60)

08:00 - OutreachSequencerAgent
        ├─ Generates personalized messages
        ├─ ComplianceAgent reviews
        └─ Sends 120 emails (to qualified + follow-ups)

Hourly - ReplyTriageAgent
         ├─ Checks inbox
         ├─ Classifies responses
         └─ Routes to conversation or booking

As needed - LeadConversationAgent
            └─ Answers questions, nurtures

As needed - BookingAgent
            └─ Proposes times, books calls

23:59 - AnalyticsAgent
        └─ Creates daily snapshot
```

## Technology Stack

**Language:** Python 3.11+

**AI:** Anthropic Claude (Sonnet 4.5)

**Database:**
- SQLAlchemy (ORM)
- SQLite (dev) / PostgreSQL (production)
- ChromaDB (vector store)

**Scheduling:** APScheduler

**APIs:**
- Google Gmail API
- Google Calendar API
- Reddit (PRAW)
- Web scraping (Requests + BeautifulSoup)

**Key Libraries:**
- `anthropic` - Claude API
- `sqlalchemy` - Database ORM
- `chromadb` - Vector database
- `apscheduler` - Job scheduling
- `praw` - Reddit API
- `google-api-python-client` - Google APIs

## Scaling Considerations

**Current (MVP):**
- Single process
- SQLite database
- Runs on one machine
- ~150 outreach/day

**Production Scale:**
- Multiple worker processes
- PostgreSQL + Redis
- Celery for distributed tasks
- ~1000+ outreach/day
- Multiple geography targets

## Security & Compliance

**Data Protection:**
- All personal data encrypted at rest
- Opt-out handling automated
- GDPR/CCPA compliant data retention

**API Security:**
- All API keys in environment variables
- OAuth tokens refreshed automatically
- Rate limiting enforced

**Message Compliance:**
- ComplianceAgent reviews all outbound messages
- Opt-out footer in all emails
- No deceptive subject lines
- Clear sender identity

## Monitoring & Analytics

**Tracked Metrics:**
- Leads by stage (funnel)
- Daily calls booked vs target
- Channel performance (Reddit vs email)
- Message template A/B test results
- Response rates by time, day, template
- Source quality (which subreddits convert best)

**Reports:**
- Daily snapshot (automated)
- Weekly performance summary
- Monthly optimization recommendations

## Extension Points

**Easy to add:**
- New lead sources (LinkedIn, Facebook, X)
- New outreach channels (SMS, WhatsApp)
- New geography targets (Texas, Florida, etc.)
- New offers (different countries, programs)
- Voice AI for call qualification
- Multi-language support

**Plugin architecture:**
- All tools are modular
- Agents use dependency injection
- Easy to swap implementations

## Design Principles

1. **Agent Specialization** - Each agent does one thing well
2. **Modularity** - Tools and agents are independent
3. **Asynchronous** - Task queue decouples execution
4. **Data-Driven** - Analytics feed back into planning
5. **Compliance-First** - Every message reviewed
6. **Human-in-Loop** - System flags edge cases for review
