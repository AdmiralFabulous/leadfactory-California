"""Source Discovery Agent - Finds high-yield lead sources."""

from agents.base_agent import BaseAgent
from tools.crm_tools import create_or_update_source, get_active_sources
from tools.web_tools import web_search
from config.settings import DEFAULT_SOURCES


class SourceDiscoveryAgent(BaseAgent):
    """Discovers and maintains list of high-yield lead sources."""

    def __init__(self):
        super().__init__("SourceDiscoveryAgent")

    def get_system_prompt(self) -> str:
        return """You are the Source Discovery Agent. Your job is to find and evaluate
online locations where Californians discuss leaving the USA, moving abroad,
or specifically moving to Portugal/Madeira.

You analyze:
- Subreddits
- Online forums
- Facebook/LinkedIn groups
- Blog communities
- Search queries that reveal intent

You prioritize sources with high engagement and clear California/USA exit intent."""

    def discover_sources(self) -> dict:
        """Discover new high-quality sources."""
        self.log("Discovering new lead sources...")

        # Start with default sources
        results = {"added": 0, "updated": 0}

        # Add default Reddit sources
        for subreddit in DEFAULT_SOURCES['reddit']['subreddits']:
            result = create_or_update_source(
                platform="reddit",
                source_name=subreddit,
                source_type="subreddit",
                source_url=f"https://reddit.com/r/{subreddit}",
                search_keywords=DEFAULT_SOURCES['reddit']['keywords'],
                is_active=True
            )
            if result['success']:
                results['added'] += 1

        # Use web search to find more forums/communities
        search_queries = [
            "california expat forum",
            "leaving california reddit",
            "moving from california to portugal",
        ]

        for query in search_queries:
            search_results = web_search(query, num_results=5)
            for result in search_results:
                # Analyze if this is a good source (simplified)
                if any(word in result['url'] for word in ['reddit.com', 'forum', 'community']):
                    self.log(f"Found potential source: {result['url']}")

        self.log(f"Source discovery complete: {results}")
        return results
