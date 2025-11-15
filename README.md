# LeadFactory California - Automated Lead Generation System

**Fully autonomous agent-based system for generating and booking 4+ qualified calls per day with Californians interested in Portuguese residency via Madeira.**

## 🎯 System Goals

- **Primary KPI:** Book 4+ Google Meet calls daily
- **Target Audience:** Californians actively wanting to leave the USA
- **Offer:** Madeira property/fund-based residency pathways via emigre.eu
- **Operation:** Fully automated with human oversight hooks

## 🏗️ Architecture Overview

This system uses a **multi-agent architecture** where specialized AI agents collaborate to:

1. **Find leads** across social platforms (Reddit, Facebook Groups, LinkedIn, forums)
2. **Enrich & qualify** leads based on location, intent, and capacity
3. **Personalize outreach** with compelling, compliant messages
4. **Handle responses** and answer questions
5. **Book meetings** automatically via Google Calendar

### System Components

```
┌─────────────────────────────────────────────────────────┐
│              ORCHESTRATOR AGENT                          │
│         (Daily planning & quota management)              │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
┌──────────────┐ ┌──────────┐ ┌──────────────┐
│ ACQUISITION  │ │ OUTREACH │ │  ANALYTICS   │
│   AGENTS     │ │  AGENTS  │ │    AGENT     │
└──────────────┘ └──────────┘ └──────────────┘
        │            │
        ▼            ▼
┌─────────────────────────────┐
│     LEAD DATABASE (CRM)      │
│  - Leads & contacts          │
│  - Outreach history          │
│  - Call bookings             │
└─────────────────────────────┘
```

### Agent Roster

1. **OrchestratorAgent** - Coordinates daily workflow to hit KPIs
2. **SourceDiscoveryAgent** - Finds high-yield lead sources
3. **LeadExtractionAgent** - Scrapes posts/profiles for candidates
4. **LeadEnrichmentAgent** - Enriches with contact info & details
5. **LeadScoringAgent** - Qualifies and prioritizes leads
6. **OfferKnowledgeAgent** - Emigre.eu expert knowledge base
7. **OutreachCopyAgent** - Writes personalized messages
8. **ComplianceAgent** - Ensures legal & platform compliance
9. **OutreachSequencerAgent** - Sends & schedules messages
10. **ReplyTriageAgent** - Classifies incoming responses
11. **LeadConversationAgent** - Answers questions, nurtures interest
12. **BookingAgent** - Schedules Google Meet calls
13. **AnalyticsAgent** - Tracks performance & optimizes

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Google Cloud account (for Gmail, Calendar APIs)
- Anthropic API key (Claude)
- Reddit account (optional, for PRAW)

### Installation

```bash
# Clone and enter directory
cd leadfactory-California

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp config/example.env .env
# Edit .env with your API keys and settings

# Initialize database
python -m database.init_db

# Load emigre.eu knowledge base
python -m services.knowledge_base_loader

# Run initial test
python main.py --mode test
```

### Running the System

```bash
# Start the automated daily system
python main.py --mode auto

# Run manual lead generation (dry run)
python main.py --mode manual --dry-run

# Run specific agent
python main.py --agent LeadExtractionAgent --count 10

# View dashboard
python dashboard.py
```

## 📘 Facebook Groups Integration (Optional)

**NEW:** Automatically scrape Facebook groups for high-quality leads!

The system now includes a Node.js-based Facebook scraper that uses Chrome DevTools MCP to automate browser interaction with Facebook groups.

### Quick Setup

```bash
# 1. Ensure Node.js 22.12.0+ is installed
node -v

# 2. Install Facebook scraper dependencies
cd facebook-scraper
npm install

# 3. Start the Facebook scraper service (keep running)
npm start
```

### Automatic Integration

Once the Facebook scraper is running, the LeadExtractionAgent automatically uses it alongside Reddit:

```bash
python main.py --mode manual --agent extract
# Will scrape both Reddit AND Facebook groups
```

### Features

- ✅ **Automated browser control** via Chrome DevTools MCP
- ✅ **Extracts posts & comments** from Facebook groups
- ✅ **Real-time progress** via WebSocket
- ✅ **Seamless Python integration** - works like any other source
- ✅ **Pre-configured groups**: Epic Retire, Americans Moving Abroad, California Exodus, Portugal Expats

### Documentation

See **[docs/FACEBOOK_INTEGRATION.md](docs/FACEBOOK_INTEGRATION.md)** for:
- Complete setup guide
- Troubleshooting
- Advanced usage
- Adding custom groups
- API reference

**Note:** Facebook scraping is optional. The system works perfectly with Reddit alone if you prefer not to use Facebook.

## 📁 Project Structure

```
leadfactory-California/
├── agents/                  # All agent implementations
│   ├── __init__.py
│   ├── base_agent.py       # Base agent class
│   ├── orchestrator.py     # OrchestratorAgent
│   ├── acquisition/        # Lead finding agents
│   │   ├── source_discovery.py
│   │   ├── lead_extraction.py
│   │   └── lead_enrichment.py
│   ├── qualification/      # Scoring & validation
│   │   └── lead_scoring.py
│   ├── outreach/           # Message & booking agents
│   │   ├── offer_knowledge.py
│   │   ├── outreach_copy.py
│   │   ├── compliance.py
│   │   ├── sequencer.py
│   │   ├── reply_triage.py
│   │   ├── conversation.py
│   │   └── booking.py
│   └── analytics/          # Analytics & optimization
│       └── analytics.py
├── tools/                  # Tool implementations
│   ├── __init__.py
│   ├── crm_tools.py       # Database operations
│   ├── email_tools.py     # Gmail API integration
│   ├── calendar_tools.py  # Google Calendar/Meet
│   ├── social_tools.py    # Reddit, LinkedIn APIs
│   ├── facebook_tools.py  # Facebook Groups scraping (NEW)
│   ├── web_tools.py       # Search & scraping
│   ├── kb_tools.py        # Knowledge base queries
│   └── task_queue.py      # Task scheduling
├── facebook-scraper/      # Facebook scraper microservice (NEW)
│   ├── server/            # Node.js Express server
│   ├── package.json       # Node.js dependencies
│   ├── README.md          # Facebook scraper docs
│   └── *.js               # Scraper scripts
├── database/              # Data persistence
│   ├── __init__.py
│   ├── models.py          # SQLAlchemy models
│   ├── init_db.py         # Database initialization
│   └── migrations/        # Schema migrations
├── services/              # External integrations
│   ├── __init__.py
│   ├── anthropic_client.py    # Claude API wrapper
│   ├── google_auth.py         # Google OAuth
│   ├── reddit_client.py       # Reddit API
│   ├── linkedin_client.py     # LinkedIn integration
│   ├── knowledge_base.py      # ChromaDB vector store
│   └── knowledge_base_loader.py
├── scheduler/             # Automation & cron
│   ├── __init__.py
│   ├── daily_scheduler.py # APScheduler jobs
│   └── task_processor.py  # Queue processor
├── config/               # Configuration
│   ├── __init__.py
│   ├── example.env       # Environment template
│   ├── settings.py       # Settings loader
│   └── agent_prompts/    # Agent system prompts
├── docs/                 # Documentation
│   ├── ARCHITECTURE.md   # System design
│   ├── AGENTS.md         # Agent specifications
│   ├── TOOLS.md          # Tool documentation
│   ├── API_SETUP.md      # API key setup guide
│   └── DEPLOYMENT.md     # Production deployment
├── tests/                # Test suite
│   ├── __init__.py
│   ├── test_agents/
│   ├── test_tools/
│   └── test_integration/
├── scripts/              # Utility scripts
│   ├── setup_google_auth.py
│   └── backup_db.py
├── data/                 # Runtime data
│   ├── leadfactory.db    # SQLite database (gitignored)
│   ├── chroma_kb/        # Vector DB (gitignored)
│   └── logs/             # Application logs (gitignored)
├── main.py               # Main entry point
├── dashboard.py          # Web dashboard (Flask)
├── requirements.txt      # Python dependencies
├── .env                  # Environment config (gitignored)
├── .gitignore
└── README.md
```

## 🔧 Configuration

### Required API Keys

Edit `.env` file:

```bash
# Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-...

# Google APIs (Gmail, Calendar, Meet)
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REFRESH_TOKEN=...  # Run setup_google_auth.py

# Reddit (optional)
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USER_AGENT=LeadFactoryBot/1.0

# LinkedIn (optional)
LINKEDIN_ACCESS_TOKEN=...

# System Config
DAILY_CALL_TARGET=4
MAX_DAILY_OUTREACH=150
TIMEZONE=America/Los_Angeles
```

### Customization

**Target Persona** (`config/settings.py`):
- Adjust qualification criteria
- Modify scoring weights
- Define outreach volume

**Message Templates** (`config/agent_prompts/outreach_copy.md`):
- Customize message tone
- A/B test variants
- Set CTA style

## 📊 Monitoring & Analytics

### Dashboard

Access real-time metrics:
```bash
python dashboard.py
# Open http://localhost:5000
```

**Metrics tracked:**
- Leads by stage (funnel)
- Daily calls booked vs target
- Channel performance (Reddit, LinkedIn, email)
- Message variant conversion rates
- Response times

### Logs

```bash
tail -f data/logs/leadfactory.log
```

## 🛡️ Compliance & Safety

**Built-in safeguards:**

1. **ComplianceAgent** reviews all outbound messages
2. Rate limiting on all platforms
3. Opt-out handling in every email
4. No deceptive subject lines or identities
5. Respects platform ToS
6. GDPR/CCPA data handling

**Manual review:**
- System flags messages for review when confidence < threshold
- All outreach logged for audit

## 🔄 Daily Workflow

**07:00** - Orchestrator evaluates quota, plans day
**07:10** - Extract ~100 raw leads from sources
**07:30** - Enrich & score leads → ~30 qualified
**08:00** - Send ~120 personalized messages
**Hourly** - Check responses, answer questions, book calls
**EOD** - Analytics report, tune for tomorrow

## 📈 Expected Performance

**Baseline conversion funnel:**
- 100 raw leads → 30 qualified → 120 messages sent (incl. follow-ups)
- 15% reply rate → 18 replies
- 50% positive/neutral → 9 interested
- 50% booking rate → 4-5 calls booked

**Optimization loop:**
- System A/B tests message variants
- Adjusts channel mix based on performance
- Learns which sources yield best leads

## 🧪 Development & Testing

```bash
# Run test suite
pytest tests/

# Test specific agent
python -m agents.acquisition.lead_extraction --test

# Dry-run outreach (no actual sends)
python main.py --mode manual --dry-run --count 5

# Database shell
python -m database.shell
```

## 🚢 Deployment

**Local/Development:**
- Run `python main.py --mode auto` in tmux/screen
- Scheduled via system cron or APScheduler

**Production (recommended):**
- Deploy to cloud VM (GCP, AWS, DigitalOcean)
- Use systemd service for daemon
- PostgreSQL instead of SQLite
- Redis for task queue
- Nginx reverse proxy for dashboard
- See `docs/DEPLOYMENT.md`

## 📞 Support & Troubleshooting

**Common issues:**

1. **No leads found** - Check source URLs, adjust search queries in `SourceDiscoveryAgent`
2. **Email not sending** - Verify Google API credentials with `scripts/setup_google_auth.py`
3. **Low response rate** - Review message templates, check spam folder placement
4. **Database locked** - Switch to PostgreSQL for production

**Debug mode:**
```bash
python main.py --mode manual --debug --verbose
```

## 🗺️ Roadmap

- [ ] V1.0 - Core system (Reddit + Email outreach)
- [ ] V1.1 - LinkedIn integration
- [ ] V1.2 - Multi-language support (Spanish for CA Latinx community)
- [ ] V1.3 - Facebook group scraping
- [ ] V2.0 - Voice AI for initial call qualification
- [ ] V2.1 - SMS outreach channel
- [ ] V2.2 - Multi-country expansion beyond California

## 📄 License

Proprietary - Internal use only

## 🙏 Credits

Built with:
- Claude by Anthropic (agent intelligence)
- Python ecosystem
- Google APIs
- Open source tools (SQLAlchemy, ChromaDB, PRAW, etc.)

---

**Version:** 1.0.0
**Last Updated:** 2025-11-15
**Maintained by:** AdmiralFabulous
