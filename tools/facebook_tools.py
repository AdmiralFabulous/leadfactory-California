"""
Facebook Group scraper tools.

Integrates with the Node.js Facebook scraper microservice to extract leads
from Facebook groups using Chrome DevTools MCP automation.
"""

from typing import List, Dict, Any, Optional
import requests
import time
from config.settings import settings


FACEBOOK_SCRAPER_URL = "http://localhost:3000"  # Default local server


def check_facebook_scraper_health() -> bool:
    """
    Check if the Facebook scraper service is running.

    Returns:
        True if service is healthy, False otherwise
    """
    try:
        response = requests.get(f"{FACEBOOK_SCRAPER_URL}/health", timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"Facebook scraper service not available: {e}")
        return False


def scrape_facebook_group(
    group_url: str,
    max_scrolls: int = 10,
    timeout: int = 300
) -> Dict[str, Any]:
    """
    Scrape a Facebook group for posts and comments.

    This calls the Node.js Facebook scraper microservice which uses
    Chrome DevTools MCP to automate browser interaction with Facebook.

    Args:
        group_url: URL of the Facebook group (e.g., https://www.facebook.com/groups/epicretire)
        max_scrolls: Maximum number of scrolls to load posts (default: 10)
        timeout: Maximum time to wait for scraping (seconds)

    Returns:
        Dict with:
            - posts: List of post dicts (author, content, timestamp, reactions, etc.)
            - comments: List of comment dicts
            - profiles: List of unique profile URLs
            - summary: Summary statistics

    Raises:
        RuntimeError: If scraper service is not running or scraping fails
    """
    if settings.dry_run:
        return {
            "posts": [
                {
                    "id": "P1",
                    "author": "John Smith",
                    "authorUrl": "https://facebook.com/john.smith",
                    "content": "Just moved to Portugal! Best decision ever.",
                    "timestamp": "2h",
                    "reactions": 42,
                    "commentCount": 8
                }
            ],
            "comments": [
                {
                    "postId": "P1",
                    "author": "Sarah Johnson",
                    "authorUrl": "https://facebook.com/sarah.johnson",
                    "content": "Congratulations! How did you handle the visa?",
                    "timestamp": "1h"
                }
            ],
            "profiles": [
                "https://facebook.com/john.smith",
                "https://facebook.com/sarah.johnson"
            ],
            "summary": {
                "totalPosts": 1,
                "totalComments": 1,
                "uniqueProfiles": 2,
                "scrapedAt": time.strftime("%Y-%m-%dT%H:%M:%S")
            }
        }

    # Check if service is running
    if not check_facebook_scraper_health():
        raise RuntimeError(
            "Facebook scraper service is not running. "
            "Start it with: cd facebook-scraper && npm install && npm start"
        )

    try:
        # Initiate scraping
        response = requests.post(
            f"{FACEBOOK_SCRAPER_URL}/api/scrape",
            json={
                "url": group_url,
                "maxScrolls": max_scrolls
            },
            timeout=timeout
        )

        response.raise_for_status()
        data = response.json()

        if not data.get("success"):
            raise RuntimeError(f"Scraping failed: {data.get('error', 'Unknown error')}")

        return data.get("data", {})

    except requests.Timeout:
        raise RuntimeError(f"Scraping timed out after {timeout} seconds")
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to communicate with Facebook scraper: {e}")


def get_facebook_scraping_status(session_id: str) -> Dict[str, Any]:
    """
    Get the status of an ongoing scraping session.

    Args:
        session_id: Session ID returned when starting a scrape

    Returns:
        Dict with status, progress, and any results
    """
    try:
        response = requests.get(
            f"{FACEBOOK_SCRAPER_URL}/api/status/{session_id}",
            timeout=5
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def search_facebook_groups(
    keywords: List[str],
    location: str = "California"
) -> List[Dict[str, Any]]:
    """
    Search for Facebook groups related to keywords and location.

    Note: This is a simple web search for Facebook groups.
    For actual Facebook API integration, you'd need official API access.

    Args:
        keywords: Search keywords (e.g., ["retire", "expat", "california"])
        location: Location filter

    Returns:
        List of potential Facebook group URLs and metadata
    """
    from tools.web_tools import web_search

    # Build search query
    query = f"site:facebook.com/groups {location} {' '.join(keywords)}"

    results = web_search(query, num_results=10)

    groups = []
    for result in results:
        if "facebook.com/groups/" in result.get("url", ""):
            groups.append({
                "name": result.get("title", ""),
                "url": result.get("url", ""),
                "description": result.get("snippet", "")
            })

    return groups


def export_facebook_data_to_csv(
    data: Dict[str, Any],
    output_dir: str = "data/facebook_exports"
) -> str:
    """
    Export Facebook scraping results to CSV.

    Args:
        data: Data dict from scrape_facebook_group()
        output_dir: Directory to save CSV files

    Returns:
        Path to the saved CSV file
    """
    import csv
    import os
    from pathlib import Path
    from datetime import datetime

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"facebook_scrape_{timestamp}.csv"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Write header
        writer.writerow([
            "Type", "Post_ID", "Author", "Author_URL",
            "Content", "Timestamp", "Reactions", "Comments"
        ])

        # Write posts
        for post in data.get("posts", []):
            writer.writerow([
                "POST",
                post.get("id", ""),
                post.get("author", ""),
                post.get("authorUrl", ""),
                post.get("content", ""),
                post.get("timestamp", ""),
                post.get("reactions", 0),
                post.get("commentCount", 0)
            ])

        # Write comments
        for comment in data.get("comments", []):
            writer.writerow([
                "COMMENT",
                comment.get("postId", ""),
                comment.get("author", ""),
                comment.get("authorUrl", ""),
                comment.get("content", ""),
                comment.get("timestamp", ""),
                "",
                ""
            ])

    return filepath


# Default Facebook groups for California expats / retirement
DEFAULT_FACEBOOK_GROUPS = [
    {
        "name": "Epic Retire",
        "url": "https://www.facebook.com/groups/epicretire",
        "keywords": ["retire", "retirement", "early retirement", "financial independence"]
    },
    {
        "name": "Americans Moving Abroad",
        "url": "https://www.facebook.com/groups/americansmovingabroad",
        "keywords": ["moving abroad", "expat", "leaving usa", "emigrate"]
    },
    {
        "name": "California Exodus",
        "url": "https://www.facebook.com/groups/californiaexodus",
        "keywords": ["leaving california", "california exodus", "moving out"]
    },
    # Add more groups as discovered
]
