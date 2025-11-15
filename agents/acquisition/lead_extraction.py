"""Lead Extraction Agent - Extracts leads from sources."""

from typing import List, Dict, Any
from agents.base_agent import BaseAgent
from tools.crm_tools import create_lead, update_lead_stage
from tools.social_tools import search_reddit_posts, search_reddit_comments
from tools.crm_tools import get_active_sources
from config.settings import settings


class LeadExtractionAgent(BaseAgent):
    """Extracts candidate leads from various sources."""

    def __init__(self):
        super().__init__("LeadExtractionAgent")

    def get_system_prompt(self) -> str:
        return """You are the Lead Extraction Agent. You find people who:
1. Live in California (or strongly appear to)
2. Express desire to leave the USA
3. Might be interested in Portugal/Madeira residency

You extract:
- Username/handle
- Source platform and URL
- Post/comment snippet showing intent
- Any location mentions

You are thorough but avoid false positives."""

    def extract_leads(self, target_count: int = 50, sources: List[str] = None) -> dict:
        """
        Extract raw leads from sources.

        Args:
            target_count: Target number of leads to find
            sources: Specific sources to use (None = use all active)

        Returns:
            Results dict
        """
        self.log(f"Extracting up to {target_count} leads...")

        if sources is None:
            sources = get_active_sources()

        leads_found = 0
        results = {"created": 0, "duplicates": 0, "errors": 0}

        # Focus on Reddit for now
        reddit_sources = [s for s in sources if s['platform'] == 'reddit']

        for source in reddit_sources[:5]:  # Limit to first 5 sources
            if leads_found >= target_count:
                break

            subreddit = source['source_name']
            keywords = source.get('keywords', [
                "leaving california",
                "leaving USA",
                "too expensive"
            ])

            self.log(f"Searching r/{subreddit}...")

            # Search posts
            posts = search_reddit_posts(
                subreddit_name=subreddit,
                keywords=keywords,
                time_filter="week",
                limit=20
            )

            for post in posts:
                if leads_found >= target_count:
                    break

                # Analyze post with Claude
                is_lead = self._analyze_potential_lead(post)

                if is_lead:
                    # Create lead
                    result = create_lead(
                        reddit_username=post['author'],
                        source_platform="reddit",
                        source_url=post['url'],
                        original_post_snippet=f"{post['title']}\n{post['body'][:500]}",
                        state="California",  # Will be validated in enrichment
                        is_californian=False,  # To be determined
                        expressed_leaving_intent=True
                    )

                    if result['success']:
                        results['created'] += 1
                        leads_found += 1
                        self.log(f"Created lead: {post['author']}")
                    else:
                        results['duplicates'] += 1

        self.log(f"Extraction complete: {results}")
        return results

    def _analyze_potential_lead(self, post: Dict[str, Any]) -> bool:
        """
        Analyze if a post indicates a potential lead.

        Args:
            post: Post dict with title and body

        Returns:
            True if this is a potential lead
        """
        # Quick heuristic check first
        text = f"{post.get('title', '')} {post.get('body', '')}".lower()

        # Must show leaving intent
        leaving_indicators = [
            "leaving", "moving out", "getting out", "escape",
            "relocate", "expat", "emigrate"
        ]
        has_leaving_intent = any(word in text for word in leaving_indicators)

        if not has_leaving_intent:
            return False

        # Bonus for California mentions
        california_indicators = [
            "california", "ca", "bay area", "los angeles",
            "san francisco", "san diego", "socal", "norcal"
        ]
        mentions_california = any(word in text for word in california_indicators)

        # Use Claude for final decision on ambiguous cases
        if has_leaving_intent and not mentions_california:
            # Quick Claude check
            prompt = f"""Is this person a good lead for California → Portugal residency?
Post: {post.get('title', '')} {post.get('body', '')[:300]}

Answer YES or NO and reason briefly."""

            response = self.think(prompt, max_tokens=100, temperature=0.3)
            return response.strip().upper().startswith("YES")

        return has_leaving_intent and mentions_california
