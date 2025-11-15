# California Priority System & Visual Dashboard

## Overview

The LeadFactory California system now includes a **California Priority System** that prioritizes Californian leads without excluding non-CA leads, plus a complete **Visual Dashboard** for monitoring and configuration.

## 🎯 Key Principles

### 1. **Priority, Not Exclusivity**

- **All leads are kept and workable** - non-CA leads remain fully visible
- **California leads get a scoring boost** - they float to the top naturally
- **Transparent scoring** - both base score and priority score are tracked
- **No filtering** - the system shows CA vs non-CA counts explicitly

### 2. **Centralized CA Detection**

The `ca_priority.py` module provides a single source of truth for California detection:

```python
from ca_priority import apply_ca_priority, is_california_location

# Apply CA priority boost
priority_score, is_ca = apply_ca_priority(
    base_score=lead_score,
    location=lead_location,
    ca_boost=2.0
)
```

**Detection Rules:**
- Matches 18+ California keywords (cities, regions, "California", "CA")
- Treats 9xxxx ZIP codes as CA (heuristic)
- Returns both priority score AND CA flag

## 📊 Visual Dashboard

### Access

The visual dashboard runs on port 5000:

```bash
# Start everything at once
python launch.py

# Or start manually
python dashboard.py
# Then visit: http://127.0.0.1:5000
```

### Features

#### 1. **Overview Page** (`/`)

Real-time metrics with auto-refresh every 5-7 seconds:

- **Total Leads** - All leads in database
- **CA Priority Leads** - Californian leads
- **Non-CA Leads** - All other valid leads (explicitly shown!)
- **CA Share %** - Percentage of CA leads
- **New Leads Today** - Leads created today
- **Avg Priority Score** - Average score after CA boost

Plus a **Recent Leads Table** showing the top 15 leads sorted by priority.

#### 2. **Leads Page** (`/leads`)

Complete leads table (300 max) with:
- Sorted by priority_score descending
- CA leads highlighted in green (#022c22 background)
- Shows both base score and priority score columns
- Clear "CA PRIORITY" vs "General" badges

#### 3. **Settings Page** (`/settings`)

Visual `.env` editor for all configuration:

**API Keys:**
- Anthropic API key
- Google OAuth credentials (Client ID, Secret, Refresh Token)
- Reddit API credentials
- LinkedIn token
- QuickScraper API key

**System Settings:**
- Timezone
- Daily call target
- Max daily outreach

**Features:**
- Saves directly to `.env` file
- Flash message confirmation
- Restart reminder for changes to take effect

#### 4. **API Endpoints**

For external integrations or custom dashboards:

- `GET /api/metrics` - JSON metrics
- `GET /api/leads?limit=50` - JSON lead list with CA flags

## 🗄️ Database Schema Updates

### New Fields in `leads` Table

```python
priority_score = Column(Float, default=0.0, index=True)  # Score after CA boost
is_ca_priority = Column(Boolean, default=False, index=True)  # CA priority flag
```

### Migration

For existing databases, run the migration script:

```bash
python scripts/migrate_ca_priority.py --db data/leadfactory.db
```

This script:
1. Adds `priority_score` and `is_ca_priority` columns
2. Creates indexes for performance
3. Populates values for all existing leads based on location

## 🔧 Integration Points

### 1. Lead Scoring Agent

**File:** `agents/qualification/lead_scoring.py`

```python
from ca_priority import apply_ca_priority

# Calculate base score first
base_score = calculate_base_score(lead)

# Apply CA priority boost
priority_score, is_ca = apply_ca_priority(
    base_score=base_score,
    location=lead.location,
    ca_boost=2.0
)

# Save both scores
update_lead(
    lead_id,
    score=base_score,
    priority_score=priority_score,
    is_ca_priority=is_ca
)
```

### 2. Main Pipeline

**File:** `main.py`

The QualificationAgent automatically:
- Calculates base score (0-100 scale)
- Applies CA priority boost (+2.0 for CA leads)
- Updates both `intent_score` (base) and `priority_score`

### 3. Outreach Sequencing

**File:** `agents/outreach/sequencer.py` or `main.py`

Leads are selected and sorted by `priority_score`:

```python
leads = (
    db.query(Lead)
    .filter(
        Lead.priority_score.isnot(None),
        Lead.intent_score >= min_score,
        Lead.email.isnot(None),
        Lead.contacted.is_(False),
    )
    .order_by(Lead.priority_score.desc())  # CA leads first!
    .limit(daily_limit)
    .all()
)
```

### 4. Dashboard Display

**File:** `dashboard.py`

The dashboard:
- Uses SQLAlchemy reflection (works with any schema)
- Automatically finds the leads table
- Computes CA priority on-the-fly for backwards compatibility
- Stores results use the DB fields directly

## 🚀 Launcher System

**File:** `launch.py`

One-command startup for the entire system:

```bash
python launch.py
```

This:
1. Starts `main.py --run-once` (agentic pipeline)
2. Starts `dashboard.py` (Flask server)
3. Waits 5 seconds for Flask to start
4. Auto-opens browser to `http://127.0.0.1:5000`
5. Handles graceful shutdown on Ctrl+C

## 📈 How CA Priority Works

### Scoring Flow

```
1. Calculate Base Score
   ├─ Location: +30 if California
   ├─ Intent: +25 if clear exit intent
   ├─ Professional: +20 if high-income proxy
   └─ Disqualifications: -25 if financial concerns

2. Apply CA Priority Boost
   ├─ Detect CA via ca_priority module
   ├─ If CA: priority_score = base_score + 2.0
   └─ If non-CA: priority_score = base_score

3. Save Both Scores
   ├─ score (or intent_score) = base_score
   ├─ priority_score = boosted score
   └─ is_ca_priority = True/False

4. Outreach Selection
   └─ ORDER BY priority_score DESC
```

### Example Scores

| Lead Type | Location | Base Score | CA Boost | Priority Score | Rank |
|-----------|----------|------------|----------|----------------|------|
| CA remote worker | San Francisco, CA | 75 | +2.0 | **77.0** | 1 |
| CA retiree | San Diego, CA | 65 | +2.0 | **67.0** | 2 |
| TX remote worker | Austin, TX | 70 | 0 | 70.0 | 3 |
| NY professional | New York, NY | 60 | 0 | 60.0 | 4 |

**Result:** CA leads are contacted first, but all qualified leads remain workable.

## 🎨 Dashboard UI

### Dark Theme

- Background: `#0f172a` (slate-900)
- Cards: `#020617` (slate-950)
- CA highlight: `#022c22` (dark green)
- Text: `#e5e7eb` (gray-200)

### Auto-Refresh

- Metrics: Every 5 seconds
- Recent leads table: Every 7 seconds
- No page reload needed

### Responsive Grid

Cards automatically adjust to screen size:
- Desktop: 3-4 columns
- Tablet: 2 columns
- Mobile: 1 column

## 🔍 Troubleshooting

### Dashboard Won't Start

```bash
# Check if port 5000 is already in use
lsof -i :5000

# Use a different port
FLASK_RUN_PORT=8080 python dashboard.py
```

### Database Not Found

```bash
# Create the data directory
mkdir -p data

# Initialize the database
python main.py --run-once
```

### Migration Script Fails

```bash
# Check database path
ls -la data/leadfactory.db

# Run with custom path
python scripts/migrate_ca_priority.py --db /path/to/your/database.db
```

### Metrics Not Updating

1. Check browser console for errors (F12)
2. Verify `/api/metrics` endpoint works: `curl http://127.0.0.1:5000/api/metrics`
3. Restart dashboard: Ctrl+C and `python dashboard.py`

## 📚 File Reference

| File | Purpose |
|------|---------|
| `ca_priority.py` | Shared CA detection module |
| `dashboard.py` | Flask visual dashboard |
| `launch.py` | One-click startup script |
| `database/models.py` | Database schema with CA fields |
| `agents/qualification/lead_scoring.py` | Scoring agent with CA priority |
| `main.py` | Simplified pipeline with CA priority |
| `scripts/migrate_ca_priority.py` | Database migration script |

## 🎯 Best Practices

### 1. **Always Use ca_priority Module**

Don't duplicate CA detection logic. Import from the centralized module:

```python
from ca_priority import apply_ca_priority, is_california_location
```

### 2. **Track Both Scores**

Always save both base score and priority score:
- `score` or `intent_score` = base score (for analysis)
- `priority_score` = boosted score (for sorting)

### 3. **Sort by Priority Score**

When selecting leads for outreach, sort by `priority_score DESC`:

```python
.order_by(Lead.priority_score.desc())
```

### 4. **Show CA/Non-CA Counts**

Don't hide non-CA leads. Show both counts explicitly:
- Dashboard shows CA vs non-CA metrics
- Leads table highlights CA leads in green
- Both types are fully visible

### 5. **Run Migration on Existing DBs**

If you have existing leads, run the migration to populate priority scores:

```bash
python scripts/migrate_ca_priority.py
```

## 🔮 Future Enhancements

Potential additions:

1. **Pipeline Status Page** - Real-time agent activity logs
2. **Source Performance Page** - Breakdown by Reddit, Facebook, etc.
3. **A/B Test Results** - Outreach template performance
4. **Lead Detail View** - Click-through to full lead profile
5. **Manual Lead Actions** - Mark as contacted, disqualified, etc.
6. **Export Functionality** - Download leads as CSV
7. **Email Template Editor** - Visual outreach message builder
8. **Calendar Integration** - Show booked calls on dashboard

## 🤝 Contributing

When adding new features:

1. Use `ca_priority.apply_ca_priority()` for CA detection
2. Update both database models (`database/models.py` and `main.py`)
3. Add migration scripts for schema changes
4. Update dashboard if adding new metrics
5. Document in this file

## 📝 Changelog

### v2.0 - CA Priority & Visual Dashboard (2025-11-15)

- ✅ Added `ca_priority.py` centralized module
- ✅ Updated database schema with `priority_score` and `is_ca_priority`
- ✅ Integrated CA priority into lead scoring agent
- ✅ Updated main.py pipeline with CA priority
- ✅ Created visual dashboard with real-time metrics
- ✅ Added settings page for .env management
- ✅ Created one-click launcher script
- ✅ Added database migration script
- ✅ Updated outreach to prioritize CA leads

### v1.0 - Initial Agentic System

- Multi-agent architecture
- Reddit + Facebook + LinkedIn integration
- Claude-powered lead qualification
- Google Calendar booking automation
