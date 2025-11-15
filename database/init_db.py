#!/usr/bin/env python3
"""
Initialize the LeadFactory database.
Run this script to create all tables.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import init_database
from database.models import (
    Lead, OutreachLog, Response, Meeting, Note,
    Source, AnalyticsSnapshot, TaskQueue
)


def main():
    """Initialize database schema."""
    print("Initializing LeadFactory California database...")
    print()

    try:
        init_database()
        print()
        print("✓ All tables created successfully:")
        print("  - leads")
        print("  - outreach_logs")
        print("  - responses")
        print("  - meetings")
        print("  - notes")
        print("  - sources")
        print("  - analytics_snapshots")
        print("  - task_queue")
        print()
        print("Database is ready!")

    except Exception as e:
        print(f"✗ Error initializing database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
