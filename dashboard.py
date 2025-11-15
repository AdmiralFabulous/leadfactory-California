"""
LeadFactory California - Control Center Dashboard
Complete visual interface for monitoring and managing the lead generation system.
"""

import os
import re
import json
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from collections import defaultdict

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
    flash,
)
from sqlalchemy import create_engine, MetaData, select, func, and_, or_
from sqlalchemy.engine import Engine
from dotenv import dotenv_values, set_key

from ca_priority import apply_ca_priority, is_california_location


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "leadfactory.db"
ENV_PATH = BASE_DIR / ".env"
LOG_PATH = BASE_DIR / "data" / "logs" / "leadfactory.log"

app = Flask(__name__)
app.secret_key = os.environ.get("DASHBOARD_SECRET_KEY", "leadfactory-secret-change-me")
app.config['TEMPLATES_AUTO_RELOAD'] = True


# ==============================================================================
# DATABASE CONNECTION
# ==============================================================================

def create_db_engine() -> Engine:
    if not DB_PATH.exists():
        print(f"[dashboard] WARNING: database file not found at {DB_PATH}")
        # Create data directory if it doesn't exist
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    url = f"sqlite:///{DB_PATH}"
    return create_engine(url, future=True, pool_pre_ping=True)


engine: Engine = create_db_engine()
metadata = MetaData()

try:
    with engine.connect() as conn:
        metadata.reflect(bind=conn)
except Exception as e:
    print(f"[dashboard] Could not reflect database: {e}")


def find_table(name_pattern: str):
    """Find a table whose name contains the pattern."""
    for name, table in metadata.tables.items():
        if name_pattern.lower() in name.lower():
            return table
    return None


LEADS_TABLE = find_table("lead")
OUTREACH_TABLE = find_table("outreach")
MEETINGS_TABLE = find_table("meeting")


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def _safe_get(row: Dict, *keys: str, default: Any = None) -> Any:
    """Safely get value from dict with fallback keys."""
    for key in keys:
        if key in row and row[key] is not None:
            return row[key]
    return default


def _format_dt(value: Any) -> str:
    """Format datetime for display."""
    if not value:
        return ""
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d %H:%M")
    return str(value)


def _format_date(value: Any) -> str:
    """Format date for display."""
    if not value:
        return ""
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    return str(value)


# ==============================================================================
# METRICS & DATA FUNCTIONS
# ==============================================================================

def get_global_stats() -> Dict[str, Any]:
    """Get high-level system statistics."""
    stats = {
        "total_leads": 0,
        "leads_today": 0,
        "calls_booked_today": 0,
        "calls_booked_total": 0,
        "daily_call_target": int(os.getenv("DAILY_CALL_TARGET", "4")),
        "ca_priority_leads": 0,
        "non_ca_leads": 0,
        "ca_share_pct": 0.0,
        "avg_priority_score": 0.0,
        "max_daily_outreach": int(os.getenv("MAX_DAILY_OUTREACH", "40")),
        "outreach_sent_today": 0,
    }

    if LEADS_TABLE is None:
        return stats

    try:
        with engine.connect() as conn:
            # Total leads
            result = conn.execute(select(func.count()).select_from(LEADS_TABLE))
            stats["total_leads"] = result.scalar() or 0

            # Today's date
            today = date.today().isoformat()

            # Leads created today
            if "created_at" in LEADS_TABLE.c:
                stmt = select(func.count()).where(
                    func.date(LEADS_TABLE.c.created_at) == today
                )
                result = conn.execute(stmt)
                stats["leads_today"] = result.scalar() or 0

            # CA priority stats
            if "is_ca_priority" in LEADS_TABLE.c:
                stmt = select(func.count()).where(LEADS_TABLE.c.is_ca_priority == True)
                result = conn.execute(stmt)
                stats["ca_priority_leads"] = result.scalar() or 0
                stats["non_ca_leads"] = stats["total_leads"] - stats["ca_priority_leads"]

            # CA share percentage
            if stats["total_leads"] > 0:
                stats["ca_share_pct"] = round(
                    (stats["ca_priority_leads"] / stats["total_leads"]) * 100, 1
                )

            # Average priority score
            if "priority_score" in LEADS_TABLE.c:
                stmt = select(func.avg(LEADS_TABLE.c.priority_score))
                result = conn.execute(stmt)
                avg = result.scalar()
                stats["avg_priority_score"] = round(float(avg), 2) if avg else 0.0

            # Calls booked today (from meetings table)
            if MEETINGS_TABLE is not None and "scheduled_at" in MEETINGS_TABLE.c:
                stmt = select(func.count()).where(
                    func.date(MEETINGS_TABLE.c.scheduled_at) == today
                )
                result = conn.execute(stmt)
                stats["calls_booked_today"] = result.scalar() or 0

                # Total booked calls
                stmt = select(func.count()).select_from(MEETINGS_TABLE)
                result = conn.execute(stmt)
                stats["calls_booked_total"] = result.scalar() or 0

            # Outreach sent today
            if OUTREACH_TABLE is not None and "created_at" in OUTREACH_TABLE.c:
                stmt = select(func.count()).where(
                    func.date(OUTREACH_TABLE.c.created_at) == today
                )
                result = conn.execute(stmt)
                stats["outreach_sent_today"] = result.scalar() or 0

    except Exception as e:
        print(f"[dashboard] Error getting global stats: {e}")

    return stats


def get_pipeline_funnel() -> Dict[str, int]:
    """Get funnel counts by stage."""
    funnel = {
        "raw": 0,
        "enriched": 0,
        "qualified": 0,
        "contacted": 0,
        "responded": 0,
        "interested": 0,
        "call_booked": 0,
        "converted": 0,
    }

    if LEADS_TABLE is None or "stage" not in LEADS_TABLE.c:
        return funnel

    try:
        with engine.connect() as conn:
            stmt = select(
                LEADS_TABLE.c.stage,
                func.count().label("count")
            ).group_by(LEADS_TABLE.c.stage)

            results = conn.execute(stmt)

            for row in results:
                stage = str(row[0]).lower() if row[0] else "unknown"
                count = row[1] or 0

                # Map stages to funnel steps
                if stage in funnel:
                    funnel[stage] = count
                elif "raw" in stage or "new" in stage:
                    funnel["raw"] += count
                elif "enriched" in stage:
                    funnel["enriched"] += count
                elif "qualified" in stage:
                    funnel["qualified"] += count
                elif "contacted" in stage:
                    funnel["contacted"] += count
                elif "responded" in stage or "replied" in stage:
                    funnel["responded"] += count
                elif "interested" in stage:
                    funnel["interested"] += count
                elif "booked" in stage or "call" in stage:
                    funnel["call_booked"] += count
                elif "converted" in stage or "closed" in stage:
                    funnel["converted"] += count

    except Exception as e:
        print(f"[dashboard] Error getting pipeline funnel: {e}")

    return funnel


def get_channel_breakdown() -> List[Dict[str, Any]]:
    """Get lead count by platform/channel."""
    channels = []

    if LEADS_TABLE is None:
        return channels

    platform_col = None
    for col_name in ["source_platform", "platform", "source", "channel"]:
        if col_name in LEADS_TABLE.c:
            platform_col = LEADS_TABLE.c[col_name]
            break

    if platform_col is None:
        return channels

    try:
        with engine.connect() as conn:
            stmt = select(
                platform_col,
                func.count().label("total"),
                func.sum(func.case((LEADS_TABLE.c.is_ca_priority == True, 1), else_=0)).label("ca_count")
                if "is_ca_priority" in LEADS_TABLE.c else func.count().label("ca_count")
            ).group_by(platform_col)

            results = conn.execute(stmt)

            for row in results:
                platform = row[0] or "unknown"
                total = row[1] or 0
                ca_count = row[2] or 0

                channels.append({
                    "platform": str(platform),
                    "count": total,
                    "ca_count": ca_count,
                    "non_ca_count": total - ca_count
                })

            # Sort by count descending
            channels.sort(key=lambda x: x["count"], reverse=True)

    except Exception as e:
        print(f"[dashboard] Error getting channel breakdown: {e}")

    return channels


def get_time_series(days: int = 30) -> Dict[str, List]:
    """Get time series data for charts."""
    series = {
        "dates": [],
        "new_leads": [],
        "qualified": [],
        "calls_booked": [],
    }

    if LEADS_TABLE is None:
        return series

    try:
        with engine.connect() as conn:
            # Get date range
            end_date = date.today()
            start_date = end_date - timedelta(days=days)

            # Fill in all dates
            current_date = start_date
            while current_date <= end_date:
                series["dates"].append(current_date.isoformat())
                current_date += timedelta(days=1)

            # Get new leads per day
            if "created_at" in LEADS_TABLE.c:
                stmt = select(
                    func.date(LEADS_TABLE.c.created_at).label("date"),
                    func.count().label("count")
                ).where(
                    func.date(LEADS_TABLE.c.created_at) >= start_date.isoformat()
                ).group_by(func.date(LEADS_TABLE.c.created_at))

                results = conn.execute(stmt)
                daily_counts = {str(row[0]): row[1] for row in results}

                series["new_leads"] = [
                    daily_counts.get(d, 0) for d in series["dates"]
                ]

            # TODO: Add qualified and calls_booked series when we have the data

    except Exception as e:
        print(f"[dashboard] Error getting time series: {e}")

    return series


def fetch_leads(
    status: Optional[str] = None,
    ca_only: bool = False,
    page: int = 1,
    page_size: int = 50
) -> Tuple[List[Dict[str, Any]], int]:
    """Fetch leads with filtering and pagination."""
    leads = []
    total = 0

    if LEADS_TABLE is None:
        return leads, total

    try:
        with engine.connect() as conn:
            # Build base query
            conditions = []

            if status:
                if "stage" in LEADS_TABLE.c:
                    conditions.append(LEADS_TABLE.c.stage == status)

            if ca_only and "is_ca_priority" in LEADS_TABLE.c:
                conditions.append(LEADS_TABLE.c.is_ca_priority == True)

            # Count total
            count_stmt = select(func.count()).select_from(LEADS_TABLE)
            if conditions:
                count_stmt = count_stmt.where(and_(*conditions))
            total = conn.execute(count_stmt).scalar() or 0

            # Get page of results
            offset = (page - 1) * page_size
            stmt = select(LEADS_TABLE)
            if conditions:
                stmt = stmt.where(and_(*conditions))

            # Order by priority score if available
            if "priority_score" in LEADS_TABLE.c:
                stmt = stmt.order_by(LEADS_TABLE.c.priority_score.desc())
            elif "created_at" in LEADS_TABLE.c:
                stmt = stmt.order_by(LEADS_TABLE.c.created_at.desc())

            stmt = stmt.limit(page_size).offset(offset)

            rows = conn.execute(stmt).mappings().all()

            for row in rows:
                lead = dict(row)
                # Format dates
                if "created_at" in lead:
                    lead["created_at_formatted"] = _format_dt(lead["created_at"])
                if "updated_at" in lead:
                    lead["updated_at_formatted"] = _format_dt(lead["updated_at"])

                leads.append(lead)

    except Exception as e:
        print(f"[dashboard] Error fetching leads: {e}")

    return leads, total


def get_recent_logs(lines: int = 200) -> List[str]:
    """Get recent log lines."""
    log_lines = []

    if not LOG_PATH.exists():
        return log_lines

    try:
        with open(LOG_PATH, 'r') as f:
            # Read last N lines
            all_lines = f.readlines()
            log_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

    except Exception as e:
        print(f"[dashboard] Error reading logs: {e}")

    return log_lines


# ==============================================================================
# ENVIRONMENT / SETTINGS MANAGEMENT
# ==============================================================================

EDITABLE_ENV_KEYS = [
    "ANTHROPIC_API_KEY",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "GOOGLE_REFRESH_TOKEN",
    "REDDIT_CLIENT_ID",
    "REDDIT_CLIENT_SECRET",
    "REDDIT_USER_AGENT",
    "LINKEDIN_ACCESS_TOKEN",
    "QUICKSCRAPER_API_KEY",
    "QUICKSCRAPER_BASE_URL",
    "DAILY_CALL_TARGET",
    "MAX_DAILY_OUTREACH",
    "TIMEZONE",
]


def load_env_config() -> Dict[str, str]:
    """Load editable environment configuration."""
    if not ENV_PATH.exists():
        return {key: "" for key in EDITABLE_ENV_KEYS}

    try:
        values = dotenv_values(ENV_PATH)
        return {key: values.get(key, "") for key in EDITABLE_ENV_KEYS}
    except Exception as e:
        print(f"[dashboard] Error loading .env: {e}")
        return {key: "" for key in EDITABLE_ENV_KEYS}


def save_env_config(updates: Dict[str, str]) -> bool:
    """Save environment configuration."""
    if not ENV_PATH.exists():
        ENV_PATH.touch()

    try:
        for key, value in updates.items():
            if key in EDITABLE_ENV_KEYS:
                set_key(ENV_PATH, key, value)
        return True
    except Exception as e:
        print(f"[dashboard] Error saving .env: {e}")
        return False


# ==============================================================================
# PAGE ROUTES
# ==============================================================================

@app.route('/')
@app.route('/dashboard')
def dashboard():
    """Home dashboard page."""
    stats = get_global_stats()
    funnel = get_pipeline_funnel()
    channels = get_channel_breakdown()
    time_series = get_time_series(days=30)

    return render_template(
        'dashboard.html',
        stats=stats,
        funnel=funnel,
        channels=channels,
        time_series=time_series,
        page='dashboard'
    )


@app.route('/pipeline')
def pipeline():
    """Pipeline and reports page."""
    stats = get_global_stats()
    funnel = get_pipeline_funnel()
    channels = get_channel_breakdown()

    return render_template(
        'pipeline.html',
        stats=stats,
        funnel=funnel,
        channels=channels,
        page='pipeline'
    )


@app.route('/leads')
def leads():
    """Leads CRM table page."""
    status = request.args.get('status')
    ca_only = request.args.get('ca_only', 'false').lower() == 'true'
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 50))

    lead_list, total = fetch_leads(status, ca_only, page, page_size)
    stats = get_global_stats()

    total_pages = (total + page_size - 1) // page_size

    return render_template(
        'leads.html',
        leads=lead_list,
        stats=stats,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        status_filter=status,
        ca_only=ca_only,
        current_page='leads'
    )


@app.route('/outreach')
def outreach():
    """Outreach and bookings page."""
    stats = get_global_stats()

    # Get recent meetings
    meetings = []
    if MEETINGS_TABLE is not None:
        try:
            with engine.connect() as conn:
                stmt = select(MEETINGS_TABLE).order_by(
                    MEETINGS_TABLE.c.scheduled_at.desc()
                ).limit(20)
                rows = conn.execute(stmt).mappings().all()
                meetings = [dict(row) for row in rows]
        except Exception as e:
            print(f"[dashboard] Error fetching meetings: {e}")

    return render_template(
        'outreach.html',
        stats=stats,
        meetings=meetings,
        page='outreach'
    )


@app.route('/agents')
def agents():
    """Agents and health monitoring page."""
    # Mock agent data - in production this would come from database
    agent_list = [
        {"name": "OrchestratorAgent", "last_run": "2 hours ago", "status": "success", "runs_today": 12},
        {"name": "LeadExtractionAgent", "last_run": "1 hour ago", "status": "success", "runs_today": 24},
        {"name": "LeadScoringAgent", "last_run": "30 minutes ago", "status": "success", "runs_today": 48},
        {"name": "OutreachSequencerAgent", "last_run": "15 minutes ago", "status": "success", "runs_today": 6},
        {"name": "ReplyTriageAgent", "last_run": "5 minutes ago", "status": "success", "runs_today": 3},
    ]

    return render_template(
        'agents.html',
        agents=agent_list,
        page='agents'
    )


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """Settings and credentials page."""
    if request.method == 'POST':
        # Save settings
        updates = {}
        for key in EDITABLE_ENV_KEYS:
            value = request.form.get(key, '').strip()
            updates[key] = value

        if save_env_config(updates):
            flash('Settings saved successfully! Restart the system to apply changes.', 'success')
        else:
            flash('Error saving settings.', 'danger')

        return redirect(url_for('settings'))

    config = load_env_config()

    return render_template(
        'settings.html',
        config=config,
        page='settings'
    )


@app.route('/logs')
def logs():
    """Logs and debug page."""
    lines = int(request.args.get('lines', 200))
    log_lines = get_recent_logs(lines)

    return render_template(
        'logs.html',
        log_lines=log_lines,
        page='logs'
    )


# ==============================================================================
# API ENDPOINTS
# ==============================================================================

@app.route('/api/progress')
def api_progress():
    """Real-time progress metrics."""
    stats = get_global_stats()
    funnel = get_pipeline_funnel()
    channels = get_channel_breakdown()

    return jsonify({
        **stats,
        "funnel": funnel,
        "channels": channels,
    })


@app.route('/api/leads')
def api_leads():
    """Paginated leads list."""
    status = request.args.get('status')
    ca_only = request.args.get('ca_only', 'false').lower() == 'true'
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('limit', 50))

    lead_list, total = fetch_leads(status, ca_only, page, page_size)

    return jsonify({
        "leads": lead_list,
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@app.route('/api/agents')
def api_agents():
    """Agent health status."""
    # Mock data - replace with actual agent monitoring
    stats = get_global_stats()
    funnel = get_pipeline_funnel()

    agent_data = {
        "Discovery": {"last_run": "Recently", "count": funnel.get("raw", 0)},
        "Extraction": {"last_run": "Recently", "count": funnel.get("enriched", 0)},
        "Enrichment": {"last_run": "Recently", "count": funnel.get("enriched", 0)},
        "Qualification": {"last_run": "Recently", "count": funnel.get("qualified", 0)},
        "Outreach": {"last_run": "Recently", "count": funnel.get("contacted", 0)},
        "Persistence": {"last_run": "Recently", "count": stats.get("total_leads", 0)},
    }

    return jsonify({
        "status": "Operational",
        "last_run": "Recently",
        "total_runs": stats.get("total_leads", 0),
        "success_rate": 100,
        "avg_duration": "2-5 minutes",
        "agents": agent_data,
        "recent_activity": []
    })


@app.route('/api/logs/tail')
def api_logs_tail():
    """Tail of logs with system info."""
    lines = int(request.args.get('lines', 200))
    filter_type = request.args.get('filter', 'all')

    log_lines = get_recent_logs(lines)

    # Apply filter
    if filter_type != 'all':
        filtered = []
        for line in log_lines:
            lower_line = line.lower()
            if filter_type == 'error' and 'error' in lower_line:
                filtered.append(line)
            elif filter_type == 'warning' and 'warning' in lower_line:
                filtered.append(line)
            elif filter_type == 'info' and 'info' in lower_line:
                filtered.append(line)
            elif filter_type in lower_line:
                filtered.append(line)
        log_lines = filtered

    # Get system info
    stats = get_global_stats()
    db_size = "Unknown"
    log_size = "Unknown"

    try:
        if DB_PATH.exists():
            db_size_bytes = DB_PATH.stat().st_size
            db_size = f"{db_size_bytes / 1024 / 1024:.2f} MB"
    except Exception:
        pass

    try:
        if LOG_PATH.exists():
            log_size_bytes = LOG_PATH.stat().st_size
            log_size = f"{log_size_bytes / 1024:.2f} KB"
    except Exception:
        pass

    system_info = {
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "db_size": db_size,
        "log_size": log_size,
        "total_records": stats.get("total_leads", 0),
        "disk_usage": "N/A"
    }

    return jsonify({
        "logs": log_lines,
        "system_info": system_info
    })


@app.route('/api/logs/download')
def api_logs_download():
    """Download full log file."""
    if not LOG_PATH.exists():
        return "Log file not found", 404

    try:
        return send_file(
            LOG_PATH,
            as_attachment=True,
            download_name="leadfactory.log",
            mimetype="text/plain"
        )
    except Exception as e:
        return f"Error downloading logs: {e}", 500


# ==============================================================================
# ACTION ENDPOINTS
# ==============================================================================

@app.route('/actions/run_once', methods=['POST'])
def action_run_once():
    """Trigger one orchestrator cycle."""
    try:
        # Run main.py --run-once
        subprocess.Popen([sys.executable, "main.py", "--run-once"], cwd=BASE_DIR)
        return jsonify({"success": True, "message": "Pipeline started"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==============================================================================
# RUN SERVER
# ==============================================================================

if __name__ == "__main__":
    port = int(os.environ.get("FLASK_PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "true").lower() == "true"

    print(f"[dashboard] Starting LeadFactory Control Center on port {port}")
    print(f"[dashboard] Visit: http://127.0.0.1:{port}")

    app.run(host="127.0.0.1", port=port, debug=debug)
