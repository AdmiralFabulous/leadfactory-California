"""
Web search and scraping tools.
"""

from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup
import json

from config.settings import settings


def web_search(
    query: str,
    num_results: int = 10,
    location: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Perform web search using Google Custom Search API.

    Args:
        query: Search query
        num_results: Number of results to return
        location: Geographic location filter

    Returns:
        List of search result dicts
    """
    if settings.dry_run:
        return [
            {
                "title": f"Mock result for: {query}",
                "url": "https://example.com",
                "snippet": "This is a mock search result",
            }
        ]

    # Check if Google Search API is configured
    if not settings.google_search_api_key or not settings.google_search_engine_id:
        print("Warning: Google Search API not configured")
        return []

    try:
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": settings.google_search_api_key,
            "cx": settings.google_search_engine_id,
            "q": query,
            "num": min(num_results, 10),  # API limit
        }

        if location:
            params["cr"] = f"country{location.upper()[:2]}"

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        results = []
        for item in data.get("items", []):
            results.append({
                "title": item.get("title"),
                "url": item.get("link"),
                "snippet": item.get("snippet"),
                "display_url": item.get("displayLink"),
            })

        return results

    except Exception as e:
        print(f"Error performing web search: {e}")
        return []


def fetch_page(url: str, timeout: int = 10) -> Optional[str]:
    """
    Fetch HTML content of a page.

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds

    Returns:
        HTML content or None on error
    """
    if settings.dry_run:
        return "<html><body>Mock HTML content</body></html>"

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.text

    except Exception as e:
        print(f"Error fetching page {url}: {e}")
        return None


def extract_text_from_html(html: str) -> str:
    """
    Extract clean text from HTML.

    Args:
        html: HTML content

    Returns:
        Cleaned text
    """
    soup = BeautifulSoup(html, 'lxml')

    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()

    # Get text
    text = soup.get_text()

    # Clean up whitespace
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)

    return text


def extract_emails_from_text(text: str) -> List[str]:
    """
    Extract email addresses from text using regex.

    Args:
        text: Text to search

    Returns:
        List of email addresses
    """
    import re
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return list(set(re.findall(email_pattern, text)))


def scrape_page_for_contacts(url: str) -> Dict[str, Any]:
    """
    Scrape a page for contact information.

    Args:
        url: URL to scrape

    Returns:
        Dict with extracted contact info
    """
    html = fetch_page(url)
    if not html:
        return {"success": False, "error": "Failed to fetch page"}

    text = extract_text_from_html(html)
    emails = extract_emails_from_text(text)

    # Look for social links
    soup = BeautifulSoup(html, 'lxml')
    social_links = {
        "linkedin": [],
        "twitter": [],
        "facebook": [],
    }

    for link in soup.find_all('a', href=True):
        href = link['href']
        if 'linkedin.com' in href:
            social_links['linkedin'].append(href)
        elif 'twitter.com' in href or 'x.com' in href:
            social_links['twitter'].append(href)
        elif 'facebook.com' in href:
            social_links['facebook'].append(href)

    return {
        "success": True,
        "url": url,
        "emails": emails,
        "social_links": {k: list(set(v)) for k, v in social_links.items()},
        "text_preview": text[:500]  # First 500 chars
    }


def enrich_person_via_web_search(
    name: str,
    location: Optional[str] = None,
    company: Optional[str] = None
) -> Dict[str, Any]:
    """
    Try to enrich a person's info using web search.

    Args:
        name: Person's name
        location: Their location (if known)
        company: Their company (if known)

    Returns:
        Enrichment data
    """
    # Build search query
    query_parts = [name]
    if location:
        query_parts.append(location)
    if company:
        query_parts.append(company)

    query = " ".join(query_parts)

    results = web_search(query, num_results=5)

    # Look for LinkedIn profiles
    linkedin_urls = [r['url'] for r in results if 'linkedin.com' in r['url']]

    return {
        "name": name,
        "search_query": query,
        "potential_linkedin": linkedin_urls[:3] if linkedin_urls else [],
        "search_results_count": len(results),
        "top_result": results[0] if results else None
    }
