# dashboard.py

import os
import re
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template_string,
    request,
    url_for,
    flash,
)
from sqlalchemy import create_engine, MetaData, select
from sqlalchemy.engine import Engine

from ca_priority import apply_ca_priority, is_california_location


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "leadfactory.db"
ENV_PATH = BASE_DIR / ".env"

app = Flask(__name__)
app.secret_key = os.environ.get("DASHBOARD_SECRET_KEY", "change-me-please")


def create_db_engine() -> Engine:
    if not DB_PATH.exists():
        print(f"[dashboard] WARNING: database file not found at {DB_PATH}")
    url = f"sqlite:///{DB_PATH}"
    return create_engine(url, future=True)


engine: Engine = create_db_engine()
metadata = MetaData()

with engine.connect() as conn:
    metadata.reflect(bind=conn)


def find_leads_table():
    """
    Try to find a table whose name contains 'lead' – works with typical schemas
    like 'leads', 'lead', 'lead_records', etc.
    """
    for name, table in metadata.tables.items():
        if "lead" in name.lower():
            return table
    return None


LEADS_TABLE = find_leads_table()


def _first_existing_column(row: Dict[str, Any], *candidates: str) -> str:
    for key in candidates:
        if key in row and row[key]:
            return str(row[key])
    return ""


def _format_dt(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, (datetime, date)):
        return value.isoformat(sep=" ", timespec="seconds")
    return str(value)


def fetch_recent_leads(limit: int = 200) -> List[Dict[str, Any]]:
    """
    Fetch recent leads from the database, annotate with CA priority metadata, and
    sort by priority_score descending.
    """
    if LEADS_TABLE is None:
        return []

    with engine.connect() as conn:
        columns = list(LEADS_TABLE.c.keys())
        if "created_at" in LEADS_TABLE.c:
            order_col = LEADS_TABLE.c.created_at
        elif "created" in LEADS_TABLE.c:
            order_col = LEADS_TABLE.c.created
        elif "id" in LEADS_TABLE.c:
            order_col = LEADS_TABLE.c.id
        else:
            # Fallback: first column
            order_col = LEADS_TABLE.c[columns[0]]

        stmt = (
            select(LEADS_TABLE)
            .order_by(order_col.desc())
            .limit(limit)
        )
        rows = conn.execute(stmt).mappings().all()

    leads: List[Dict[str, Any]] = []

    for row in rows:
        data = dict(row)

        # Determine location field heuristically
        location_value = _first_existing_column(
            data,
            "location",
            "city",
            "region",
            "state",
            "country",
            "geo",
        )

        # Determine base score (if any)
        base_score_raw = data.get("priority_score", data.get("score"))
        try:
            base_score = float(base_score_raw) if base_score_raw is not None else 0.0
        except (TypeError, ValueError):
            base_score = 0.0

        # If the DB already has explicit CA flags, respect them; otherwise derive.
        existing_is_ca = data.get("is_ca_priority")
        derived_priority_score, derived_is_ca = apply_ca_priority(
            base_score=base_score,
            location=location_value,
        )

        if isinstance(existing_is_ca, bool):
            is_ca_priority = existing_is_ca or derived_is_ca
        else:
            is_ca_priority = derived_is_ca

        if "priority_score" in data and data["priority_score"] is not None:
            priority_score = float(data["priority_score"])
        else:
            priority_score = derived_priority_score

        data["__location"] = location_value
        data["__is_ca_priority"] = bool(is_ca_priority)
        data["__base_score"] = float(base_score)
        data["__priority_score"] = float(priority_score)

        # Normalised friendly fields for display
        data["__display_name"] = data.get("name") or data.get("full_name") or ""
        data["__display_email"] = data.get("email") or data.get("primary_email") or ""
        data["__display_source"] = data.get("source") or data.get("channel") or ""
        data["__display_stage"] = data.get("status") or data.get("stage") or ""
        data["__display_created_at"] = _format_dt(
            data.get("created_at") or data.get("created")
        )

        leads.append(data)

    leads.sort(key=lambda r: r["__priority_score"], reverse=True)
    return leads


def compute_metrics() -> Dict[str, Any]:
    """
    Aggregate high-level metrics for the overview page and API.
    """
    metrics: Dict[str, Any] = {
        "total_leads": 0,
        "ca_leads": 0,
        "non_ca_leads": 0,
        "today_leads": 0,
        "avg_priority_score": 0.0,
        "ca_share_pct": 0.0,
    }

    leads = fetch_recent_leads(limit=10000)
    if not leads:
        return metrics

    today_iso = date.today().isoformat()
    scores: List[float] = []

    for lead in leads:
        metrics["total_leads"] += 1

        if lead["__is_ca_priority"]:
            metrics["ca_leads"] += 1
        else:
            metrics["non_ca_leads"] += 1

        created_str = lead.get("__display_created_at") or ""
        if created_str.startswith(today_iso):
            metrics["today_leads"] += 1

        scores.append(lead["__priority_score"])

    if scores:
        metrics["avg_priority_score"] = round(
            sum(scores) / max(len(scores), 1),
            2,
        )

    if metrics["total_leads"] > 0:
        metrics["ca_share_pct"] = round(
            metrics["ca_leads"] / metrics["total_leads"] * 100.0,
            1,
        )

    return metrics


ENV_KEYS = [
    "ANTHROPIC_API_KEY",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "GOOGLE_REFRESH_TOKEN",
    "REDDIT_CLIENT_ID",
    "REDDIT_CLIENT_SECRET",
    "REDDIT_USER_AGENT",
    "LINKEDIN_ACCESS_TOKEN",
    "QUICKSCRAPER_API_KEY",
    "TIMEZONE",
    "DAILY_CALL_TARGET",
    "MAX_DAILY_OUTREACH",
]


def load_env() -> Tuple[Dict[str, str], list]:
    """
    Load known keys from .env and keep the rest of the file so we can
    preserve comments and unknown settings.
    """
    values: Dict[str, str] = {key: "" for key in ENV_KEYS}
    other_lines: list = []

    if not ENV_PATH.exists():
        return values, other_lines

    with ENV_PATH.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")
            if not line or line.lstrip().startswith("#"):
                other_lines.append(line)
                continue
            if "=" not in line:
                other_lines.append(line)
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            if key in values:
                values[key] = val
            else:
                other_lines.append(line)

    return values, other_lines


def save_env(new_values: Dict[str, str], other_lines: list) -> None:
    """
    Rewrite .env with updated known keys and preserved other lines.
    """
    lines: list = []
    lines.append("# LeadFactory configuration (managed by dashboard)")
    for key in ENV_KEYS:
        value = new_values.get(key, "")
        lines.append(f"{key}={value}")

    if other_lines:
        lines.append("")
        lines.append("# Other settings")
        lines.extend(other_lines)

    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


BASE_CSS = """
body {
    font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    margin: 0;
    padding: 0;
    background-color: #0f172a;
    color: #e5e7eb;
}
a {
    color: #38bdf8;
    text-decoration: none;
}
a:hover {
    text-decoration: underline;
}
nav {
    background-color: #020617;
    padding: 0.75rem 1.5rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid #1f2937;
}
nav .brand {
    font-weight: 600;
    font-size: 1.1rem;
}
nav .links a {
    margin-left: 1rem;
    font-size: 0.95rem;
}
.container {
    padding: 1.5rem;
}
.grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 1rem;
}
.card {
    background-color: #020617;
    border-radius: 0.75rem;
    padding: 1rem 1.1rem;
    border: 1px solid #1f2937;
}
.card h2 {
    margin: 0 0 0.25rem 0;
    font-size: 0.95rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #9ca3af;
}
.card .value {
    font-size: 1.6rem;
    font-weight: 600;
}
.card .sub {
    font-size: 0.8rem;
    color: #9ca3af;
}
.badge {
    display: inline-block;
    padding: 0.1rem 0.45rem;
    border-radius: 999px;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}
.badge-success {
    background-color: #05966933;
    color: #6ee7b7;
}
.badge-warning {
    background-color: #f59e0b33;
    color: #fbbf24;
}
.badge-muted {
    background-color: #4b556333;
    color: #9ca3af;
}
table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;
}
th, td {
    padding: 0.45rem 0.4rem;
    border-bottom: 1px solid #1f2937;
}
th {
    text-align: left;
    font-weight: 600;
    color: #9ca3af;
    font-size: 0.8rem;
}
tr:hover td {
    background-color: #020617;
}
tr.ca-priority td {
    background-color: #022c22;
}
.flash {
    padding: 0.75rem 1rem;
    margin-bottom: 1rem;
    border-radius: 0.5rem;
    font-size: 0.85rem;
}
.flash-success {
    background-color: #065f46;
    color: #d1fae5;
}
.flash-error {
    background-color: #7f1d1d;
    color: #fecaca;
}
.form-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 1rem;
}
.form-field label {
    display: block;
    font-size: 0.8rem;
    color: #9ca3af;
    margin-bottom: 0.25rem;
}
.form-field input {
    width: 100%;
    padding: 0.45rem 0.5rem;
    border-radius: 0.5rem;
    border: 1px solid #374151;
    background-color: #020617;
    color: #e5e7eb;
    font-size: 0.85rem;
}
button {
    border-radius: 0.5rem;
    border: none;
    cursor: pointer;
    padding: 0.45rem 0.85rem;
    font-size: 0.85rem;
}
.btn-primary {
    background-color: #0ea5e9;
    color: #0f172a;
}
.btn-secondary {
    background-color: #111827;
    color: #e5e7eb;
    border: 1px solid #374151;
}
.badge-ca {
    background-color: #4ade8033;
    color: #bbf7d0;
}
.badge-nonca {
    background-color: #47556933;
    color: #cbd5f5;
}
.small {
    font-size: 0.78rem;
    color: #9ca3af;
}
"""


OVERVIEW_TEMPLATE = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>LeadFactory Dashboard</title>
    <style>
    {{ css }}
    </style>
  </head>
  <body>
    <nav>
      <div class="brand">LeadFactory • Visual Dashboard</div>
      <div class="links">
        <a href="{{ url_for('overview') }}">Overview</a>
        <a href="{{ url_for('leads_view') }}">Leads</a>
        <a href="{{ url_for('settings_view') }}">Settings</a>
      </div>
    </nav>
    <div class="container">
      <div class="grid">
        <div class="card">
          <h2>Total Leads</h2>
          <div class="value" id="metric-total">{{ metrics.total_leads }}</div>
          <div class="sub">All leads in database</div>
        </div>
        <div class="card">
          <h2>CA Priority Leads</h2>
          <div class="value" id="metric-ca">{{ metrics.ca_leads }}</div>
          <div class="sub">Californian (priority) leads</div>
        </div>
        <div class="card">
          <h2>Non-CA Leads</h2>
          <div class="value" id="metric-nonca">{{ metrics.non_ca_leads }}</div>
          <div class="sub">All other valid leads (included, not excluded)</div>
        </div>
        <div class="card">
          <h2>CA Share</h2>
          <div class="value" id="metric-ca-share">{{ metrics.ca_share_pct }}%</div>
          <div class="sub">CA priority share of total</div>
        </div>
        <div class="card">
          <h2>New Leads Today</h2>
          <div class="value" id="metric-today">{{ metrics.today_leads }}</div>
          <div class="sub">Leads created today (local time)</div>
        </div>
        <div class="card">
          <h2>Avg Priority Score</h2>
          <div class="value" id="metric-avg">{{ metrics.avg_priority_score }}</div>
          <div class="sub">Score after CA boost where applicable</div>
        </div>
      </div>

      <h2 style="margin-top: 2rem; font-size: 1rem;">Recent Leads (sorted by priority)</h2>
      <p class="small">
        Californians are highlighted and boosted, but all leads are kept and shown.
      </p>
      <div class="card">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Lead</th>
              <th>Email</th>
              <th>Source</th>
              <th>Stage</th>
              <th>Location</th>
              <th>Score</th>
              <th>Priority</th>
              <th>CA?</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody id="recent-leads-body">
          {% for lead in leads %}
            <tr class="{{ 'ca-priority' if lead.__is_ca_priority else '' }}">
              <td>{{ lead.get('id', '') }}</td>
              <td>{{ lead.__display_name }}</td>
              <td>{{ lead.__display_email }}</td>
              <td>{{ lead.__display_source }}</td>
              <td>{{ lead.__display_stage }}</td>
              <td>{{ lead.__location }}</td>
              <td>{{ "%.2f"|format(lead.__base_score) }}</td>
              <td>{{ "%.2f"|format(lead.__priority_score) }}</td>
              <td>
                {% if lead.__is_ca_priority %}
                  <span class="badge badge-ca">CA PRIORITY</span>
                {% else %}
                  <span class="badge badge-muted">General</span>
                {% endif %}
              </td>
              <td>{{ lead.__display_created_at }}</td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
    </div>

    <script>
    async function refreshMetrics() {
      try {
        const res = await fetch("{{ url_for('api_metrics') }}");
        if (!res.ok) return;
        const data = await res.json();
        const t = document.getElementById("metric-total");
        const ca = document.getElementById("metric-ca");
        const nonca = document.getElementById("metric-nonca");
        const share = document.getElementById("metric-ca-share");
        const today = document.getElementById("metric-today");
        const avg = document.getElementById("metric-avg");
        if (t) t.textContent = data.total_leads ?? 0;
        if (ca) ca.textContent = data.ca_leads ?? 0;
        if (nonca) nonca.textContent = data.non_ca_leads ?? 0;
        if (share) share.textContent = (data.ca_share_pct ?? 0).toFixed(1) + "%";
        if (today) today.textContent = data.today_leads ?? 0;
        if (avg) avg.textContent = (data.avg_priority_score ?? 0).toFixed(2);
      } catch (err) {
        console.warn("Failed to refresh metrics:", err);
      }
    }

    async function refreshRecentLeads() {
      try {
        const res = await fetch("{{ url_for('api_leads') }}?limit=30");
        if (!res.ok) return;
        const data = await res.json();
        const body = document.getElementById("recent-leads-body");
        if (!body) return;
        body.innerHTML = "";
        for (const lead of data) {
          const tr = document.createElement("tr");
          if (lead.is_ca_priority) {
            tr.classList.add("ca-priority");
          }
          tr.innerHTML = `
            <td>${lead.id ?? ""}</td>
            <td>${lead.name ?? ""}</td>
            <td>${lead.email ?? ""}</td>
            <td>${lead.source ?? ""}</td>
            <td>${lead.status ?? ""}</td>
            <td>${lead.location ?? ""}</td>
            <td>${(lead.score ?? 0).toFixed(2)}</td>
            <td>${(lead.priority_score ?? 0).toFixed(2)}</td>
            <td>${
              lead.is_ca_priority
                ? '<span class="badge badge-ca">CA PRIORITY</span>'
                : '<span class="badge badge-muted">General</span>'
            }</td>
            <td>${lead.created_at ?? ""}</td>
          `;
          body.appendChild(tr);
        }
      } catch (err) {
        console.warn("Failed to refresh leads:", err);
      }
    }

    function startAutoRefresh() {
      refreshMetrics();
      refreshRecentLeads();
      setInterval(refreshMetrics, 5000);
      setInterval(refreshRecentLeads, 7000);
    }

    window.addEventListener("load", startAutoRefresh);
    </script>
  </body>
</html>
"""


LEADS_TEMPLATE = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>LeadFactory • Leads</title>
    <style>
    {{ css }}
    </style>
  </head>
  <body>
    <nav>
      <div class="brand">LeadFactory • Leads</div>
      <div class="links">
        <a href="{{ url_for('overview') }}">Overview</a>
        <a href="{{ url_for('leads_view') }}">Leads</a>
        <a href="{{ url_for('settings_view') }}">Settings</a>
      </div>
    </nav>
    <div class="container">
      <h1 style="font-size: 1rem; margin-bottom: 0.25rem;">All Leads (sorted by priority)</h1>
      <p class="small">
        Californians are given a scoring boost and highlighted in green, but non-CA leads
        are still fully visible and available for outreach.
      </p>
      <div class="card" style="overflow-x: auto;">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Lead</th>
              <th>Email</th>
              <th>Source</th>
              <th>Stage</th>
              <th>Location</th>
              <th>Score</th>
              <th>Priority Score</th>
              <th>CA?</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
          {% for lead in leads %}
            <tr class="{{ 'ca-priority' if lead.__is_ca_priority else '' }}">
              <td>{{ lead.get('id', '') }}</td>
              <td>{{ lead.__display_name }}</td>
              <td>{{ lead.__display_email }}</td>
              <td>{{ lead.__display_source }}</td>
              <td>{{ lead.__display_stage }}</td>
              <td>{{ lead.__location }}</td>
              <td>{{ "%.2f"|format(lead.__base_score) }}</td>
              <td>{{ "%.2f"|format(lead.__priority_score) }}</td>
              <td>
                {% if lead.__is_ca_priority %}
                  <span class="badge badge-ca">CA PRIORITY</span>
                {% else %}
                  <span class="badge badge-nonca">General</span>
                {% endif %}
              </td>
              <td>{{ lead.__display_created_at }}</td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
    </div>
  </body>
</html>
"""


SETTINGS_TEMPLATE = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>LeadFactory • Settings</title>
    <style>
    {{ css }}
    </style>
  </head>
  <body>
    <nav>
      <div class="brand">LeadFactory • Settings</div>
      <div class="links">
        <a href="{{ url_for('overview') }}">Overview</a>
        <a href="{{ url_for('leads_view') }}">Leads</a>
        <a href="{{ url_for('settings_view') }}">Settings</a>
      </div>
    </nav>
    <div class="container">
      {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
          {% for category, msg in messages %}
            <div class="flash flash-{{ 'success' if category == 'success' else 'error' }}">{{ msg }}</div>
          {% endfor %}
        {% endif %}
      {% endwith %}

      <h1 style="font-size: 1rem; margin-bottom: 0.25rem;">Configuration</h1>
      <p class="small">
        Edit API keys and system settings. Changes are written to <code>.env</code>.
        You should restart <code>main.py</code> (or the launcher) after saving.
      </p>

      <form method="post">
        <div class="form-grid">
          <div class="form-field">
            <label for="ANTHROPIC_API_KEY">Anthropic Claude API key</label>
            <input id="ANTHROPIC_API_KEY" name="ANTHROPIC_API_KEY" type="password"
                   value="{{ env.ANTHROPIC_API_KEY }}">
          </div>
          <div class="form-field">
            <label for="GOOGLE_CLIENT_ID">Google Client ID</label>
            <input id="GOOGLE_CLIENT_ID" name="GOOGLE_CLIENT_ID" type="text"
                   value="{{ env.GOOGLE_CLIENT_ID }}">
          </div>
          <div class="form-field">
            <label for="GOOGLE_CLIENT_SECRET">Google Client Secret</label>
            <input id="GOOGLE_CLIENT_SECRET" name="GOOGLE_CLIENT_SECRET" type="password"
                   value="{{ env.GOOGLE_CLIENT_SECRET }}">
          </div>
          <div class="form-field">
            <label for="GOOGLE_REFRESH_TOKEN">Google Refresh Token</label>
            <input id="GOOGLE_REFRESH_TOKEN" name="GOOGLE_REFRESH_TOKEN" type="password"
                   value="{{ env.GOOGLE_REFRESH_TOKEN }}">
          </div>
          <div class="form-field">
            <label for="REDDIT_CLIENT_ID">Reddit Client ID</label>
            <input id="REDDIT_CLIENT_ID" name="REDDIT_CLIENT_ID" type="text"
                   value="{{ env.REDDIT_CLIENT_ID }}">
          </div>
          <div class="form-field">
            <label for="REDDIT_CLIENT_SECRET">Reddit Client Secret</label>
            <input id="REDDIT_CLIENT_SECRET" name="REDDIT_CLIENT_SECRET" type="password"
                   value="{{ env.REDDIT_CLIENT_SECRET }}">
          </div>
          <div class="form-field">
            <label for="REDDIT_USER_AGENT">Reddit User Agent</label>
            <input id="REDDIT_USER_AGENT" name="REDDIT_USER_AGENT" type="text"
                   value="{{ env.REDDIT_USER_AGENT }}">
          </div>
          <div class="form-field">
            <label for="LINKEDIN_ACCESS_TOKEN">LinkedIn Access Token</label>
            <input id="LINKEDIN_ACCESS_TOKEN" name="LINKEDIN_ACCESS_TOKEN" type="password"
                   value="{{ env.LINKEDIN_ACCESS_TOKEN }}">
          </div>
          <div class="form-field">
            <label for="QUICKSCRAPER_API_KEY">QuickScraper API Key</label>
            <input id="QUICKSCRAPER_API_KEY" name="QUICKSCRAPER_API_KEY" type="password"
                   value="{{ env.QUICKSCRAPER_API_KEY }}">
          </div>
          <div class="form-field">
            <label for="TIMEZONE">Timezone</label>
            <input id="TIMEZONE" name="TIMEZONE" type="text"
                   value="{{ env.TIMEZONE }}">
          </div>
          <div class="form-field">
            <label for="DAILY_CALL_TARGET">Daily Call Target</label>
            <input id="DAILY_CALL_TARGET" name="DAILY_CALL_TARGET" type="number" step="1"
                   value="{{ env.DAILY_CALL_TARGET }}">
          </div>
          <div class="form-field">
            <label for="MAX_DAILY_OUTREACH">Max Daily Outreach</label>
            <input id="MAX_DAILY_OUTREACH" name="MAX_DAILY_OUTREACH" type="number" step="1"
                   value="{{ env.MAX_DAILY_OUTREACH }}">
          </div>
        </div>
        <div style="margin-top: 1rem;">
          <button type="submit" class="btn-primary">Save Settings</button>
          <a href="{{ url_for('overview') }}" class="btn-secondary" style="margin-left: 0.5rem;">Cancel</a>
        </div>
      </form>
    </div>
  </body>
</html>
"""


@app.route("/")
def overview():
    metrics = compute_metrics()
    leads = fetch_recent_leads(limit=15)
    return render_template_string(
        OVERVIEW_TEMPLATE,
        css=BASE_CSS,
        metrics=metrics,
        leads=leads,
    )


@app.route("/leads")
def leads_view():
    leads = fetch_recent_leads(limit=300)
    return render_template_string(
        LEADS_TEMPLATE,
        css=BASE_CSS,
        leads=leads,
    )


@app.route("/settings", methods=["GET", "POST"])
def settings_view():
    env_values, other_lines = load_env()
    if request.method == "POST":
        new_values: Dict[str, str] = {}
        for key in ENV_KEYS:
            new_values[key] = request.form.get(key, "").strip()
        save_env(new_values, other_lines)
        flash("Settings saved. Restart the main process or launcher to apply changes.", "success")
        return redirect(url_for("settings_view"))

    return render_template_string(
        SETTINGS_TEMPLATE,
        css=BASE_CSS,
        env=env_values,
    )


@app.route("/api/metrics")
def api_metrics():
    return jsonify(compute_metrics())


@app.route("/api/leads")
def api_leads():
    limit = request.args.get("limit", default=50, type=int)
    leads = fetch_recent_leads(limit=limit)
    payload: List[Dict[str, Any]] = []
    for lead in leads:
        payload.append(
            {
                "id": lead.get("id"),
                "name": lead.get("__display_name"),
                "email": lead.get("__display_email"),
                "source": lead.get("__display_source"),
                "status": lead.get("__display_stage"),
                "location": lead.get("__location"),
                "score": lead.get("__base_score"),
                "priority_score": lead.get("__priority_score"),
                "is_ca_priority": lead.get("__is_ca_priority"),
                "created_at": lead.get("__display_created_at"),
            }
        )
    return jsonify(payload)


if __name__ == "__main__":
    # Default to localhost:5000 as per README
    app.run(host="127.0.0.1", port=5000, debug=True)
