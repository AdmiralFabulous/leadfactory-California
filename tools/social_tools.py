"""
Social media tools for Reddit, LinkedIn, etc.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import praw
from config.settings import settings


# ============================================================================
# REDDIT
# ============================================================================

def get_reddit_client():
    """Get authenticated Reddit client."""
    if not settings.has_reddit_auth():
        raise ValueError("Reddit authentication not configured")

    return praw.Reddit(
        client_id=settings.reddit_client_id,
        client_secret=settings.reddit_client_secret,
        user_agent=settings.reddit_user_agent
    )


def search_reddit_posts(
    subreddit_name: str,
    keywords: List[str],
    time_filter: str = "week",
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Search Reddit posts in a subreddit.

    Args:
        subreddit_name: Subreddit name (without r/)
        keywords: Search keywords
        time_filter: "hour", "day", "week", "month", "year", "all"
        limit: Max posts to return

    Returns:
        List of post dicts with author, content, url
    """
    if settings.dry_run:
        return []

    try:
        reddit = get_reddit_client()
        subreddit = reddit.subreddit(subreddit_name)

        posts = []
        for keyword in keywords:
            for submission in subreddit.search(keyword, time_filter=time_filter, limit=limit):
                # Skip if deleted/removed
                if submission.author is None:
                    continue

                posts.append({
                    "id": submission.id,
                    "title": submission.title,
                    "body": submission.selftext,
                    "author": str(submission.author),
                    "url": f"https://reddit.com{submission.permalink}",
                    "score": submission.score,
                    "num_comments": submission.num_comments,
                    "created_utc": datetime.fromtimestamp(submission.created_utc).isoformat(),
                    "subreddit": subreddit_name,
                })

        return posts

    except Exception as e:
        print(f"Error searching Reddit: {e}")
        return []


def get_reddit_comments(
    subreddit_name: str,
    keywords: List[str],
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Get Reddit comments containing keywords.

    Args:
        subreddit_name: Subreddit name
        keywords: Keywords to search for
        limit: Max comments to return

    Returns:
        List of comment dicts
    """
    if settings.dry_run:
        return []

    try:
        reddit = get_reddit_client()
        subreddit = reddit.subreddit(subreddit_name)

        comments = []
        for comment in subreddit.comments(limit=limit):
            # Check if comment contains any keyword
            if comment.author is None or comment.body is None:
                continue

            body_lower = comment.body.lower()
            if any(keyword.lower() in body_lower for keyword in keywords):
                comments.append({
                    "id": comment.id,
                    "body": comment.body,
                    "author": str(comment.author),
                    "url": f"https://reddit.com{comment.permalink}",
                    "score": comment.score,
                    "created_utc": datetime.fromtimestamp(comment.created_utc).isoformat(),
                    "subreddit": subreddit_name,
                })

        return comments

    except Exception as e:
        print(f"Error getting Reddit comments: {e}")
        return []


def get_reddit_user_profile(username: str) -> Optional[Dict[str, Any]]:
    """
    Get public info about a Reddit user.

    Args:
        username: Reddit username

    Returns:
        User profile dict or None
    """
    if settings.dry_run:
        return None

    try:
        reddit = get_reddit_client()
        user = reddit.redditor(username)

        return {
            "username": username,
            "link_karma": user.link_karma,
            "comment_karma": user.comment_karma,
            "created_utc": datetime.fromtimestamp(user.created_utc).isoformat(),
            "is_gold": user.is_gold,
        }

    except Exception as e:
        print(f"Error getting Reddit user: {e}")
        return None


def send_reddit_dm(username: str, subject: str, message: str) -> Dict[str, Any]:
    """
    Send a DM to a Reddit user.

    Args:
        username: Reddit username
        subject: Message subject
        message: Message body

    Returns:
        Result dict
    """
    if settings.dry_run:
        return {
            "success": True,
            "dry_run": True,
            "to": username,
            "subject": subject
        }

    try:
        reddit = get_reddit_client()
        reddit.redditor(username).message(subject, message)

        return {
            "success": True,
            "to": username,
            "subject": subject
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "to": username
        }


# ============================================================================
# LINKEDIN (Placeholder - API access is restricted)
# ============================================================================

def send_linkedin_message(profile_url: str, message: str) -> Dict[str, Any]:
    """
    Send LinkedIn message.

    Note: LinkedIn severely restricts API access. This is a placeholder.
    In production, you'd use:
    - LinkedIn's official API (requires partnership)
    - Unofficial libraries (against ToS, risky)
    - Manual browser automation (Selenium/Playwright)

    Args:
        profile_url: LinkedIn profile URL
        message: Message to send

    Returns:
        Result dict
    """
    if settings.dry_run or True:  # Always dry run for now
        return {
            "success": True,
            "dry_run": True,
            "note": "LinkedIn messaging requires manual setup or partnership",
            "profile_url": profile_url
        }

    # TODO: Implement if you get LinkedIn API access
    # For now, this would require manual browser automation
    return {
        "success": False,
        "error": "LinkedIn API not implemented - requires manual process or partnership",
        "profile_url": profile_url
    }


def search_linkedin_profiles(keywords: List[str], location: str = "California") -> List[Dict[str, Any]]:
    """
    Search LinkedIn profiles.

    Note: This is a placeholder. Real implementation would require:
    - LinkedIn API partnership
    - Web scraping (against ToS)
    - Manual browser automation

    Args:
        keywords: Search keywords
        location: Geographic filter

    Returns:
        List of profile dicts
    """
    # Placeholder - not implemented
    return []
