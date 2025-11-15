#!/usr/bin/env python3
"""
Database migration script to add CA priority fields.

This script adds priority_score and is_ca_priority columns to existing leads tables
and populates them based on existing data.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import sqlite3
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from ca_priority import apply_ca_priority


def migrate_database(db_path: str = "data/leadfactory.db"):
    """Add CA priority fields to leads table and populate them."""

    print(f"Migrating database: {db_path}")

    # Connect using SQLite directly for schema changes
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if columns already exist
    cursor.execute("PRAGMA table_info(leads)")
    columns = [row[1] for row in cursor.fetchall()]

    needs_migration = False

    if "priority_score" not in columns:
        print("Adding priority_score column...")
        cursor.execute("ALTER TABLE leads ADD COLUMN priority_score REAL DEFAULT 0.0")
        needs_migration = True
    else:
        print("✓ priority_score column already exists")

    if "is_ca_priority" not in columns:
        print("Adding is_ca_priority column...")
        cursor.execute("ALTER TABLE leads ADD COLUMN is_ca_priority INTEGER DEFAULT 0")
        needs_migration = True
    else:
        print("✓ is_ca_priority column already exists")

    conn.commit()

    if needs_migration:
        # Create indexes
        print("Creating indexes...")
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_priority_score ON leads(priority_score)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ca_priority ON leads(is_ca_priority, priority_score)")
            conn.commit()
            print("✓ Indexes created")
        except Exception as e:
            print(f"Index creation note: {e}")

    conn.close()

    # Now use SQLAlchemy to populate the values
    print("\nPopulating CA priority values for existing leads...")

    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Get all leads
        result = session.execute(text("""
            SELECT id, score, intent_score, location, city, state
            FROM leads
            WHERE priority_score IS NULL OR priority_score = 0
        """))

        leads = result.fetchall()
        print(f"Found {len(leads)} leads to update")

        updated = 0
        for lead in leads:
            lead_id, score, intent_score, location, city, state = lead

            # Build location string
            location_parts = []
            if city:
                location_parts.append(city)
            if state:
                location_parts.append(state)
            if location:
                location_parts.append(location)
            location_str = ', '.join(filter(None, location_parts)) if location_parts else None

            # Use intent_score or score as base
            base_score = intent_score if intent_score is not None else (score if score is not None else 0.0)

            # Apply CA priority
            priority_score, is_ca = apply_ca_priority(
                base_score=base_score,
                location=location_str,
                ca_boost=2.0
            )

            # Update the lead
            session.execute(
                text("""
                    UPDATE leads
                    SET priority_score = :priority_score,
                        is_ca_priority = :is_ca
                    WHERE id = :id
                """),
                {
                    "priority_score": priority_score,
                    "is_ca": 1 if is_ca else 0,
                    "id": lead_id
                }
            )
            updated += 1

            if updated % 100 == 0:
                print(f"  Updated {updated} leads...")

        session.commit()
        print(f"✓ Updated {updated} leads with CA priority scores")

    except Exception as e:
        print(f"Error during migration: {e}")
        session.rollback()
        raise
    finally:
        session.close()

    print("\n✓ Migration complete!")
    print("\nSummary:")
    print("- Added priority_score and is_ca_priority columns")
    print("- Created indexes for performance")
    print(f"- Populated values for {updated} existing leads")
    print("\nCA leads will now be prioritized in outreach sorting.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Migrate database to add CA priority fields")
    parser.add_argument(
        "--db",
        default="data/leadfactory.db",
        help="Path to database file (default: data/leadfactory.db)"
    )
    args = parser.parse_args()

    migrate_database(args.db)
