"""Lead Extraction Agent - Extracts leads from sources."""

from typing import List, Dict, Any
from agents.base_agent import BaseAgent
from tools.crm_tools import create_lead, update_lead_stage
from tools.social_tools import search_reddit_posts, search_reddit_comments
from tools.facebook_tools import scrape_facebook_group, check_facebook_scraper_health
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
        results = {"created": 0, "duplicates": 0, "errors": 0, "facebook": 0, "reddit": 0}

        # Extract from Reddit
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
                        results['reddit'] += 1
                        leads_found += 1
                        self.log(f"Created lead: {post['author']}")
                    else:
                        results['duplicates'] += 1

        # Extract from Facebook Groups (if scraper is available)
        if leads_found < target_count:
            facebook_sources = [s for s in sources if s['platform'] == 'facebook']

            if facebook_sources and check_facebook_scraper_health():
                self.log("Facebook scraper available - extracting from Facebook groups...")

                for source in facebook_sources[:3]:  # Limit to 3 Facebook groups
                    if leads_found >= target_count:
                        break

                    group_url = source.get('source_url')
                    if not group_url:
                        continue

                    self.log(f"Scraping Facebook group: {source['source_name']}...")

                    try:
                        # Scrape the Facebook group
                        fb_data = scrape_facebook_group(group_url, max_scrolls=5)

                        # Process posts from Facebook
                        for post in fb_data.get('posts', []):
                            if leads_found >= target_count:
                                break

                            # Check if post shows exit intent
                            content = post.get('content', '')
                            if self._analyze_facebook_post(content):
                                # Create lead
                                author = post.get('author', 'Unknown')
                                author_url = post.get('authorUrl', '')

                                result = create_lead(
                                    first_name=author.split()[0] if author else '',
                                    last_name=' '.join(author.split()[1:]) if len(author.split()) > 1 else '',
                                    source_platform="facebook",
                                    source_url=author_url or group_url,
                                    original_post_snippet=content[:500],
                                    state="California",  # Will be validated in enrichment
                                    is_californian=False,  # To be determined
                                    expressed_leaving_intent=True
                                )

                                if result['success']:
                                    results['created'] += 1
                                    results['facebook'] += 1
                                    leads_found += 1
                                    self.log(f"Created Facebook lead: {author}")
                                else:
                                    results['duplicates'] += 1

                    except Exception as e:
                        self.log(f"Error scraping Facebook group: {e}")
                        results['errors'] += 1

            else:
                if facebook_sources:
                    self.log("Facebook scraper not available - skipping Facebook sources")
                    self.log("Start with: cd facebook-scraper && npm install && npm start")

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

    def _analyze_facebook_post(self, content: str) -> bool:
        """
        Analyze if a Facebook post indicates a potential lead.

        Args:
            content: Post content text

        Returns:
            True if this is a potential lead
        """
        if not content:
            return False

        content_lower = content.lower()

        # Check for leaving intent
        leaving_indicators = [
            "leaving", "moving out", "getting out", "escape",
            "relocate", "expat", "emigrate", "retire abroad",
            "leaving usa", "leaving california", "move abroad"
        ]
        has_leaving_intent = any(word in content_lower for word in leaving_indicators)

        if not has_leaving_intent:
            return False

        # Check for California connection
        california_indicators = [
            "california", "ca", "bay area", "los angeles",
            "san francisco", "san diego", "socal", "norcal",
            "sacramento", "oakland", "san jose"
        ]
        mentions_california = any(word in content_lower for word in california_indicators)

        # Check for Portugal/Madeira interest (bonus)
        portugal_indicators = [
            "portugal", "madeira", "lisbon", "porto", "golden visa",
            "d7 visa", "nhr", "portuguese"
        ]
        mentions_portugal = any(word in content_lower for word in portugal_indicators)

        # Higher confidence if both California and leaving intent, or if Portugal mentioned
        if mentions_portugal:
            return True

        return has_leaving_intent and (mentions_california or len(content) > 100)
