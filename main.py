#!/usr/bin/env python3
"""
LeadFactory California - Main entry point
Automated lead generation system for Portuguese residency via Madeira.
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import settings
from database import init_database
from scheduler import DailyScheduler


def setup():
    """Initial setup and validation."""
    print("=" * 70)
    print("LeadFactory California - Automated Lead Generation System")
    print("=" * 70)
    print()

    # Check database
    print("Checking database...")
    try:
        init_database()
        print("✓ Database ready")
    except Exception as e:
        print(f"✗ Database error: {e}")
        return False

    # Check API keys
    print("\nChecking configuration...")
    if not settings.anthropic_api_key:
        print("✗ ANTHROPIC_API_KEY not set")
        return False
    print("✓ Anthropic API key configured")

    if settings.has_google_auth():
        print("✓ Google APIs configured")
    else:
        print("⚠ Google APIs not configured (email/calendar features disabled)")

    if settings.has_reddit_auth():
        print("✓ Reddit API configured")
    else:
        print("⚠ Reddit API not configured (limited lead sources)")

    print()
    return True


def run_auto_mode():
    """Run in automatic mode with scheduler."""
    print("Starting automated mode...")
    print(f"Target: {settings.daily_call_target} calls per day")
    print(f"Max outreach: {settings.max_daily_outreach} messages per day")
    print()

    scheduler = DailyScheduler()
    scheduler.start()

    print()
    print("✓ System is running!")
    print("  Press Ctrl+C to stop")
    print()

    try:
        # Keep running
        import time
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        scheduler.stop()
        print("Goodbye!")


def run_manual_mode(agent_name: str = None, dry_run: bool = False):
    """Run specific agent manually."""
    if dry_run:
        print("DRY RUN MODE - No actual API calls will be made")
        import config.settings as settings_module
        settings_module.settings.dry_run = True

    if agent_name == "orchestrator":
        from agents import OrchestratorAgent
        agent = OrchestratorAgent()
        result = agent.run_daily_plan()
        print(f"\nResult: {result}")

    elif agent_name == "extract":
        from agents import LeadExtractionAgent
        agent = LeadExtractionAgent()
        result = agent.extract_leads(target_count=10)
        print(f"\nResult: {result}")

    elif agent_name == "enrich":
        from agents import LeadEnrichmentAgent
        agent = LeadEnrichmentAgent()
        result = agent.enrich_leads(batch_size=10)
        print(f"\nResult: {result}")

    elif agent_name == "score":
        from agents import LeadScoringAgent
        agent = LeadScoringAgent()
        result = agent.score_leads()
        print(f"\nResult: {result}")

    elif agent_name == "outreach":
        from agents import OutreachSequencerAgent
        agent = OutreachSequencerAgent()
        result = agent.send_outreach_batch()
        print(f"\nResult: {result}")

    elif agent_name == "responses":
        from agents import ReplyTriageAgent
        agent = ReplyTriageAgent()
        result = agent.process_new_responses()
        print(f"\nResult: {result}")

    else:
        print(f"Unknown agent: {agent_name}")
        print("Available: orchestrator, extract, enrich, score, outreach, responses")


def run_test_mode():
    """Run system tests."""
    print("Running system tests...\n")

    # Test database
    print("1. Testing database...")
    try:
        from tools.crm_tools import create_lead, get_pipeline_stats
        result = create_lead(
            email="test@example.com",
            first_name="Test",
            last_name="Lead",
            state="California"
        )
        if result['success']:
            print("   ✓ Database working")
        stats = get_pipeline_stats()
        print(f"   ✓ Pipeline stats: {stats}")
    except Exception as e:
        print(f"   ✗ Database test failed: {e}")

    # Test Claude API
    print("\n2. Testing Claude API...")
    try:
        from services.anthropic_client import get_claude_client
        claude = get_claude_client()
        response = claude.generate_with_context(
            prompt="Say 'API working' if you can read this.",
            max_tokens=50
        )
        print(f"   ✓ Claude API working: {response[:50]}")
    except Exception as e:
        print(f"   ✗ Claude API test failed: {e}")

    # Test knowledge base
    print("\n3. Testing knowledge base...")
    try:
        from tools.kb_tools import add_knowledge_document, search_knowledge_base
        add_knowledge_document(
            doc_id="test_doc",
            content="Madeira offers golden visa through property investment.",
            metadata={"type": "test"}
        )
        results = search_knowledge_base("golden visa")
        print(f"   ✓ Knowledge base working: {len(results)} results")
    except Exception as e:
        print(f"   ✗ Knowledge base test failed: {e}")

    print("\n✓ Basic tests complete!")


def show_stats():
    """Show current system statistics."""
    from tools.crm_tools import get_pipeline_stats, get_todays_meetings

    stats = get_pipeline_stats()
    meetings = get_todays_meetings()

    print("=" * 70)
    print("CURRENT SYSTEM STATUS")
    print("=" * 70)
    print()
    print(f"Calls booked today: {stats.get('calls_booked_today', 0)} / {settings.daily_call_target}")
    print(f"Outreach sent today: {stats.get('outreach_sent_today', 0)} / {settings.max_daily_outreach}")
    print(f"Responses today: {stats.get('responses_today', 0)}")
    print()
    print("Pipeline:")
    print(f"  Raw leads: {stats.get('stage_raw', 0)}")
    print(f"  Enriched: {stats.get('stage_enriched', 0)}")
    print(f"  Qualified: {stats.get('stage_qualified', 0)}")
    print(f"  Contacted: {stats.get('stage_contacted', 0)}")
    print(f"  Responded: {stats.get('stage_responded', 0)}")
    print(f"  Interested: {stats.get('stage_interested', 0)}")
    print(f"  Calls booked: {stats.get('stage_call_booked', 0)}")
    print()
    print(f"Today's meetings: {len(meetings)}")
    for meeting in meetings:
        print(f"  - {meeting['scheduled_at']}: {meeting['lead_name']}")
    print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="LeadFactory California - Automated Lead Generation"
    )

    parser.add_argument(
        '--mode',
        choices=['auto', 'manual', 'test', 'stats'],
        default='auto',
        help='Execution mode'
    )

    parser.add_argument(
        '--agent',
        help='Agent to run in manual mode (orchestrator, extract, enrich, score, outreach, responses)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run mode (no actual API calls)'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )

    args = parser.parse_args()

    # Set debug mode
    if args.debug:
        import config.settings as settings_module
        settings_module.settings.debug = True
        settings_module.settings.log_level = "DEBUG"

    # Run setup checks
    if not setup():
        print("\n✗ Setup failed. Please fix configuration and try again.")
        sys.exit(1)

    # Execute based on mode
    if args.mode == 'auto':
        run_auto_mode()
    elif args.mode == 'manual':
        if not args.agent:
            print("Error: --agent required for manual mode")
            print("Example: python main.py --mode manual --agent extract")
            sys.exit(1)
        run_manual_mode(args.agent, args.dry_run)
    elif args.mode == 'test':
        run_test_mode()
    elif args.mode == 'stats':
        show_stats()


if __name__ == "__main__":
    main()
