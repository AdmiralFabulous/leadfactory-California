#!/usr/bin/env python3
"""
Knowledge base loader for emigre.eu content.
Fetches and indexes content about Madeira residency options.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.kb_tools import add_knowledge_document, get_all_knowledge_documents
from tools.web_tools import fetch_page, extract_text_from_html


def load_emigre_knowledge():
    """Load emigre.eu content into knowledge base."""
    print("=" * 70)
    print("Loading emigre.eu Knowledge Base")
    print("=" * 70)
    print()

    # Core knowledge to add (simplified for MVP)
    # In production, you'd scrape emigre.eu or use provided docs

    knowledge_docs = [
        {
            "id": "madeira_overview",
            "content": """Madeira Golden Visa Overview:

Portugal's Golden Visa program allows non-EU citizens to obtain residency through investment.
Madeira, an autonomous region of Portugal, offers unique advantages:

- Lower property prices than mainland Portugal
- Excellent climate year-round
- English widely spoken
- Modern infrastructure
- EU residency benefits
- Path to citizenship after 5 years

Investment options:
1. Property investment: €500,000+ in qualifying real estate
2. Capital transfer: €1.5 million to Portuguese bank
3. Fund investment: €500,000 in qualifying investment funds
4. Business creation: Create 10+ jobs

Madeira-specific benefits:
- Reduced tax rates under NHR (Non-Habitual Resident) program
- 0-20% income tax for qualifying activities
- Lifestyle: beaches, mountains, safe community
- Strategic location: 90 min flight to Lisbon, direct to major EU cities""",
            "metadata": {
                "category": "overview",
                "source": "emigre.eu",
                "topic": "golden_visa"
            }
        },
        {
            "id": "property_investment",
            "content": """Property Investment Pathway:

Minimum investment: €500,000 in qualifying property
(Or €400,000 in low-density areas - most of Madeira qualifies)

Process:
1. Visit Madeira, view properties (emigre.eu can arrange)
2. Select property and reserve
3. Open Portuguese bank account
4. Transfer funds (documented)
5. Complete purchase via lawyer
6. Apply for Golden Visa
7. Receive residency card (typically 6-12 months)

Requirements:
- Clean criminal record
- Health insurance
- Proof of funds
- Minimum 7 days/year in Portugal (very flexible!)

Property can be:
- Residential (apartment, villa)
- Commercial (rentable)
- Renovation projects (must spend €350k+ on renovation)

Benefits:
- Rental income possible
- Appreciation potential
- EU residency for whole family
- Travel freely in Schengen zone
- Path to Portuguese citizenship""",
            "metadata": {
                "category": "investment",
                "source": "emigre.eu",
                "topic": "property"
            }
        },
        {
            "id": "fund_investment",
            "content": """Fund Investment Pathway:

Minimum investment: €500,000 in qualifying investment funds

Advantages over property:
- More liquid than real estate
- Diversified risk
- No property management
- Same residency benefits

Qualifying funds:
- Must be approved by Portuguese authorities
- Typically focus on Portuguese companies, real estate, or innovation
- emigre.eu partners with approved fund managers

Process:
1. Select approved fund
2. Transfer €500,000 to fund
3. Maintain investment for minimum 5 years
4. Apply for Golden Visa
5. Receive residency card

Ideal for:
- Those who don't want property management
- Investors seeking diversification
- People focused on passive investment

Returns vary by fund, typically 3-7% annually.
All funds are regulated and approved by Portuguese government.""",
            "metadata": {
                "category": "investment",
                "source": "emigre.eu",
                "topic": "funds"
            }
        },
        {
            "id": "tax_benefits",
            "content": """Portuguese Tax Benefits:

Non-Habitual Resident (NHR) Program:
- Available to new Portuguese residents
- 10 years of tax benefits
- 0-20% tax on qualifying foreign income
- Ideal for remote workers, retirees, entrepreneurs

Madeira-specific:
- Free Trade Zone with additional benefits
- Reduced corporate tax rates
- IP/licensing income can be tax-optimized

For remote workers:
- If income qualifies as "high value-added," can be taxed at 20% flat rate
- Tech, consulting, creative work often qualifies
- Much lower than California rates (37%+ federal + 13.3% state)

For retirees:
- Pension income can qualify for 0-10% tax
- Social Security not taxed by US-Portugal treaty
- No wealth tax
- No estate tax

For entrepreneurs:
- Madeira Free Trade Zone offers corporate tax as low as 5%
- Holding company structures available
- R&D tax credits

Important: Professional tax advice essential for your situation.""",
            "metadata": {
                "category": "benefits",
                "source": "emigre.eu",
                "topic": "taxation"
            }
        },
        {
            "id": "lifestyle",
            "content": """Life in Madeira:

Climate:
- Subtropical, 16-26°C year-round
- "Island of eternal spring"
- Low humidity, comfortable
- Minimal seasonal variation

Safety:
- One of safest regions in Europe
- Very low crime rate
- Political stability
- Excellent healthcare

Community:
- Growing expat community (UK, EU, US, South Africa)
- English widely spoken, especially in Funchal
- International schools available
- Welcoming to foreigners

Cost of Living:
- Lower than California (30-50% less)
- Quality restaurants: €10-20/person
- Rent: €800-2000/month (2-bed apartment)
- Healthcare: Public (free) or private (affordable)

Activities:
- Hiking (levada walks, mountain trails)
- Water sports (surfing, diving, sailing)
- Golf courses
- Wine tourism (Madeira wine famous worldwide)
- Direct flights to Lisbon, London, Frankfurt, etc.

Infrastructure:
- Fast fiber internet (remote work friendly)
- Modern airport
- Good roads
- Reliable utilities

Work:
- Growing tech/startup scene
- Co-working spaces in Funchal
- Digital nomad community
- Time zone: GMT (works well for US East Coast, Europe)""",
            "metadata": {
                "category": "lifestyle",
                "source": "emigre.eu",
                "topic": "living"
            }
        },
        {
            "id": "process_timeline",
            "content": """Golden Visa Timeline:

Month 0: Initial research & consultation
- Understand options
- Assess eligibility
- Plan finances

Month 1-2: Visit Madeira
- View properties or meet fund managers
- Explore the island
- Make decision

Month 2-3: Initiate investment
- Reserve property / Select fund
- Open bank account
- Engage lawyer
- Transfer funds

Month 3-4: Complete investment
- Finalize purchase
- Get all documentation
- Prepare visa application

Month 4-6: Apply for Golden Visa
- Submit application at Portuguese consulate or via lawyer in Portugal
- Provide all required docs
- Pay fees

Month 6-12: Receive residency card
- First card valid 2 years
- Renewable for 3-year periods
- Very minimal stay requirement (7 days/year)

Year 5: Eligible for permanent residency
Year 6: Eligible to apply for Portuguese citizenship
- Requires basic Portuguese language test (A2 level)
- Grants full EU citizenship
- Dual citizenship allowed (US, Canada, etc.)

emigre.eu supports throughout entire process.""",
            "metadata": {
                "category": "process",
                "source": "emigre.eu",
                "topic": "timeline"
            }
        }
    ]

    # Load documents
    loaded = 0
    for doc in knowledge_docs:
        result = add_knowledge_document(
            doc_id=doc['id'],
            content=doc['content'],
            metadata=doc['metadata']
        )

        if result['success']:
            print(f"✓ Loaded: {doc['id']}")
            loaded += 1
        else:
            print(f"✗ Failed: {doc['id']} - {result.get('error')}")

    print()
    print("=" * 70)
    print(f"✓ Loaded {loaded}/{len(knowledge_docs)} documents into knowledge base")
    print("=" * 70)

    # Verify
    all_docs = get_all_knowledge_documents()
    print(f"\nTotal documents in KB: {len(all_docs)}")

    return loaded


def refresh_from_web():
    """
    Optionally fetch fresh content from emigre.eu.
    (Placeholder - implement if you want live scraping)
    """
    print("Web scraping not implemented in MVP.")
    print("Using hardcoded knowledge base.")
    print("In production, you'd scrape emigre.eu or use their API.")


if __name__ == "__main__":
    load_emigre_knowledge()
