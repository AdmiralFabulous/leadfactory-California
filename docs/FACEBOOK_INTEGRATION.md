# Facebook Groups Integration

The LeadFactory California system now includes automated Facebook group scraping capabilities using Chrome DevTools MCP (Model Context Protocol). This allows you to extract leads from Facebook groups where Californians discuss leaving the USA, retirement abroad, and expat life.

## Overview

**What it does:**
- Automatically navigates Facebook groups using browser automation
- Extracts posts and comments from group members
- Identifies people expressing interest in leaving California/USA
- Creates lead records with names, profile URLs, and content
- Works alongside Reddit and other lead sources

**Technology:**
- **Node.js server** (`facebook-scraper/`) - Handles browser automation
- **Chrome DevTools MCP** - Automates Chrome browser
- **Python integration** - Seamless integration with existing agents
- **Real-time progress** - WebSocket updates during scraping

---

## Prerequisites

1. **Node.js 22.12.0 or newer**
   ```bash
   node -v  # Check your version
   ```
   If you need to upgrade, use [nvm](https://github.com/nvm-sh/nvm) or download from [nodejs.org](https://nodejs.org/)

2. **Active Facebook account**
   - You'll need to log into Facebook when the browser launches
   - The scraper uses your logged-in session to access groups

3. **Python requirements already installed**
   - The main `requirements.txt` already has everything needed

---

## Setup

### 1. Install Facebook Scraper Dependencies

```bash
cd facebook-scraper
npm install
```

This installs:
- `chrome-devtools-mcp` - Browser automation
- `express` - Web server
- `socket.io` - Real-time updates
- Other dependencies

### 2. Start the Facebook Scraper Service

```bash
# From facebook-scraper/ directory
npm start
```

You should see:
```
Facebook Scraper Server running on http://localhost:3000
WebSocket server ready
```

**Keep this terminal open** - the service needs to run alongside the main Python system.

### 3. Verify Service is Running

```bash
# From main project directory
python -c "from tools.facebook_tools import check_facebook_scraper_health; print('OK' if check_facebook_scraper_health() else 'Not running')"
```

---

## Usage

### Automatic Mode (Integrated with LeadFactory)

Once the Facebook scraper service is running, the LeadExtractionAgent automatically uses it:

```bash
# Run normal lead generation
python main.py --mode manual --agent extract

# The agent will:
# 1. Extract leads from Reddit
# 2. Check if Facebook scraper is available
# 3. Extract leads from Facebook groups (if available)
# 4. Combine all leads
```

### Manual Facebook Scraping (Python)

```python
from tools.facebook_tools import scrape_facebook_group

# Scrape a specific Facebook group
data = scrape_facebook_group(
    group_url="https://www.facebook.com/groups/epicretire",
    max_scrolls=10  # How many times to scroll (more = more posts)
)

# Results
print(f"Found {len(data['posts'])} posts")
print(f"Found {len(data['comments'])} comments")
print(f"Found {len(data['profiles'])} unique profiles")

# Access posts
for post in data['posts']:
    print(f"{post['author']}: {post['content'][:100]}")
```

### Direct API Access

The Facebook scraper also exposes a REST API:

```bash
# Scrape a group
curl -X POST http://localhost:3000/api/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.facebook.com/groups/epicretire", "maxScrolls": 5}'

# Check service health
curl http://localhost:3000/health
```

---

## Default Facebook Groups

The system is pre-configured with these high-quality groups:

1. **Epic Retire** - Early retirement discussions
   - https://www.facebook.com/groups/epicretire
   - Keywords: retire, retirement, early retirement, financial independence

2. **Americans Moving Abroad** - Expat community
   - https://www.facebook.com/groups/americansmovingabroad
   - Keywords: moving abroad, expat, leaving usa, emigrate

3. **California Exodus** - People leaving California
   - https://www.facebook.com/groups/californiaexodus
   - Keywords: leaving california, california exodus, moving out

4. **Portugal Expats** - Portugal-specific community
   - https://www.facebook.com/groups/portugalexpats
   - Keywords: portugal, madeira, golden visa, d7 visa

These are added automatically when you run SourceDiscoveryAgent.

---

## Adding Custom Facebook Groups

### Via Configuration (Recommended)

Edit `config/settings.py` and add to `DEFAULT_SOURCES['facebook']['groups']`:

```python
{
    "name": "Your Group Name",
    "url": "https://www.facebook.com/groups/groupname",
    "keywords": ["keyword1", "keyword2", "keyword3"]
}
```

Then re-run SourceDiscoveryAgent to add to database:

```bash
python main.py --mode manual --agent source_discovery
```

### Via Database (Advanced)

```python
from tools.crm_tools import create_or_update_source

create_or_update_source(
    platform="facebook",
    source_name="Your Group Name",
    source_type="facebook_group",
    source_url="https://www.facebook.com/groups/groupname",
    search_keywords=["keyword1", "keyword2"],
    is_active=True
)
```

---

## How It Works

### Architecture

```
┌─────────────────────────────────────────┐
│  Python LeadFactory System               │
│  ├─ LeadExtractionAgent                  │
│  └─ tools/facebook_tools.py              │
│          │                                │
│          │ HTTP/WebSocket                 │
│          ▼                                │
│  ┌───────────────────────────────────┐  │
│  │  Node.js Facebook Scraper         │  │
│  │  (facebook-scraper/server/)       │  │
│  │  ├─ Express server (port 3000)    │  │
│  │  └─ Socket.IO for real-time       │  │
│  └───────────────────────────────────┘  │
│          │                                │
│          │ Spawns                         │
│          ▼                                │
│  ┌───────────────────────────────────┐  │
│  │  Chrome DevTools MCP              │  │
│  │  ├─ Launches Chrome browser       │  │
│  │  ├─ Navigates to Facebook         │  │
│  │  ├─ Scrolls to load posts         │  │
│  │  └─ Takes accessibility snapshot  │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

### Scraping Process

1. **Browser Launch** - Chrome DevTools MCP starts isolated Chrome instance
2. **Navigation** - Navigates to Facebook group URL
3. **Authentication** - User logs in (first time only, then stays logged in)
4. **Scrolling** - Scrolls page to load more posts
5. **Snapshot** - Captures accessibility tree (DOM structure)
6. **Parsing** - Extracts posts, authors, content, reactions, comments
7. **Return Data** - Structured JSON with posts, comments, profiles

---

## Data Format

### Returned Data Structure

```json
{
  "posts": [
    {
      "id": "P1",
      "author": "John Smith",
      "authorUrl": "https://facebook.com/john.smith",
      "content": "Just retired after 30 years in tech!",
      "timestamp": "2h",
      "reactions": 15,
      "commentCount": 3,
      "badge": "Top contributor"
    }
  ],
  "comments": [
    {
      "postId": "P1",
      "author": "Sarah Johnson",
      "authorUrl": "https://facebook.com/sarah.johnson",
      "content": "Congratulations!",
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
    "scrapedAt": "2025-11-15T12:00:00Z"
  }
}
```

### How Leads are Created

When a Facebook post shows exit intent, a lead is created with:
- **Name**: Extracted from author field
- **Profile URL**: Facebook profile link
- **Source**: "facebook"
- **Content**: Post content snippet
- **State**: "California" (validated in enrichment)
- **Intent flags**: `expressed_leaving_intent = True`

---

## Troubleshooting

### Facebook Scraper Service Won't Start

**Error:** `Cannot find module 'express'`
```bash
cd facebook-scraper
npm install
```

**Error:** `Node version too old`
```bash
node -v  # Check version
# Upgrade to Node.js 22.12.0+ using nvm or installer
```

**Port 3000 already in use:**
```bash
# Find process using port 3000
lsof -i :3000  # Mac/Linux
netstat -ano | findstr :3000  # Windows

# Kill it or change port in facebook-scraper/server/index.js
```

### Facebook Login Issues

**Problem:** Browser keeps asking for login

- **Solution 1:** Log in manually when browser opens, check "Keep me logged in"
- **Solution 2:** Use Facebook session cookies (advanced - see MCP docs)
- **Solution 3:** Adjust session timeout in browser automation

**Problem:** "Checkpoint required" or "Unusual activity"

- Facebook detected automation
- Try:
  1. Log into Facebook manually in your regular browser first
  2. Reduce `max_scrolls` to scrape fewer posts
  3. Add delays between requests
  4. Use Facebook less frequently

### No Leads Being Created

**Check 1:** Is service running?
```python
from tools.facebook_tools import check_facebook_scraper_health
print(check_facebook_scraper_health())  # Should be True
```

**Check 2:** Are Facebook sources in database?
```python
from tools.crm_tools import get_active_sources
sources = get_active_sources()
fb_sources = [s for s in sources if s['platform'] == 'facebook']
print(f"Facebook sources: {len(fb_sources)}")
```

**Check 3:** Run source discovery:
```bash
python main.py --mode manual --agent source_discovery
```

**Check 4:** Check logs:
```bash
tail -f data/logs/leadfactory.log
```

### Rate Limiting / Slow Scraping

- Facebook has rate limits to prevent abuse
- **Recommendation:** Scrape 1-2 groups per day max
- Use `max_scrolls=5` to limit posts extracted
- Spread out scraping across different times of day

---

## Best Practices

### 1. Respectful Scraping

- ✅ Join groups you legitimately care about
- ✅ Contribute value to communities
- ✅ Use scraping to find relevant people, not spam
- ❌ Don't scrape private/closed groups you're not a member of
- ❌ Don't over-scrape (respect rate limits)

### 2. Privacy & Compliance

- Only scrape **public posts** in **public groups**
- Respect Facebook's Terms of Service
- Don't store sensitive personal data
- Include opt-out mechanisms in outreach
- Follow GDPR/CCPA guidelines

### 3. Optimal Settings

```python
# Good: Moderate, sustainable scraping
scrape_facebook_group(url, max_scrolls=5)

# Avoid: Too aggressive
scrape_facebook_group(url, max_scrolls=50)  # Takes too long, may trigger limits
```

### 4. Combining Sources

Best results come from using Facebook + Reddit + Web:

```python
# In LeadExtractionAgent
# Will automatically use:
# 1. Reddit (fast, many posts)
# 2. Facebook (slower, high-quality leads)
# 3. Web search (fallback)
```

---

## Advanced Usage

### Export to CSV

```python
from tools.facebook_tools import scrape_facebook_group, export_facebook_data_to_csv

data = scrape_facebook_group("https://www.facebook.com/groups/epicretire")
csv_path = export_facebook_data_to_csv(data)
print(f"Exported to: {csv_path}")
```

### Custom Filtering

```python
from tools.facebook_tools import scrape_facebook_group

data = scrape_facebook_group("...")

# Filter posts by reactions
hot_posts = [p for p in data['posts'] if p['reactions'] > 20]

# Filter by keywords
portugal_posts = [
    p for p in data['posts']
    if 'portugal' in p['content'].lower() or 'madeira' in p['content'].lower()
]
```

### Batch Scraping Multiple Groups

```python
from tools.facebook_tools import scrape_facebook_group
from tools.crm_tools import get_active_sources
import time

sources = get_active_sources()
fb_sources = [s for s in sources if s['platform'] == 'facebook']

all_data = {
    'posts': [],
    'comments': [],
    'profiles': set()
}

for source in fb_sources[:3]:  # Limit to 3 groups
    print(f"Scraping {source['source_name']}...")

    data = scrape_facebook_group(source['source_url'], max_scrolls=5)

    all_data['posts'].extend(data['posts'])
    all_data['comments'].extend(data['comments'])
    all_data['profiles'].update(data['profiles'])

    # Be respectful - wait between groups
    time.sleep(60)  # 1 minute delay

print(f"Total: {len(all_data['posts'])} posts, {len(all_data['profiles'])} profiles")
```

---

## Development & Testing

### Run in Dry-Run Mode

```bash
# Python side (uses mock data)
python main.py --mode manual --agent extract --dry-run

# This will NOT actually scrape Facebook
# Uses pre-defined mock data instead
```

### Test Scraper Directly

```bash
cd facebook-scraper
node test-scrape.js
```

### View Real-Time Progress

The Facebook scraper emits WebSocket events you can monitor:

```javascript
// Connect to Socket.IO for progress updates
const socket = io('http://localhost:3000');

socket.on('scraping-progress', (data) => {
  console.log(`Status: ${data.status}`);
  console.log(`Message: ${data.message}`);
  console.log(`Progress: ${data.progress.posts} posts, ${data.progress.comments} comments`);
});
```

---

## Performance

**Speed:**
- ~10-30 seconds per Facebook group (depends on `max_scrolls`)
- Reddit scraping is faster (~5-10 seconds)

**Volume:**
- Typical group scrape: 10-30 posts per run
- With comments: 20-100 total leads per group
- Quality > quantity (Facebook tends to have more detailed posts)

**Resource Usage:**
- Chrome browser: ~200-500MB RAM
- Node.js server: ~50-100MB RAM
- Python system: ~100-200MB RAM

---

## Security Notes

1. **Facebook Session:** Your Facebook login session is used for scraping
   - Browser runs in isolated mode (separate from your normal Chrome)
   - Session cookies stored temporarily
   - Log out manually if concerned

2. **API Keys:** No Facebook API keys required
   - Uses browser automation (MCP)
   - No official Facebook API needed

3. **Data Storage:** Scraped data stored in local database
   - Same privacy/security as other leads
   - Subject to GDPR/CCPA compliance requirements

---

## Updating Facebook Scraper

To get the latest version:

```bash
cd facebook-scraper
npm update
```

To update Chrome DevTools MCP:

```bash
cd facebook-scraper
npm install chrome-devtools-mcp@latest
```

---

## Alternative: Manual Facebook Data

If you don't want to run the automated scraper, you can manually export Facebook group data:

1. Open Facebook group in browser
2. Copy posts manually
3. Use the Python tool to create leads:

```python
from tools.crm_tools import create_lead

create_lead(
    first_name="John",
    last_name="Smith",
    source_platform="facebook",
    source_url="https://facebook.com/john.smith",
    original_post_snippet="Just moved to Portugal...",
    state="California",
    expressed_leaving_intent=True
)
```

---

## Support

For Facebook scraper issues:
1. Check this documentation
2. Review logs: `tail -f data/logs/leadfactory.log`
3. Test service health: `curl http://localhost:3000/health`
4. Check Node.js version: `node -v`
5. Restart services

For Chrome DevTools MCP issues:
- See [chrome-devtools-mcp docs](https://github.com/ChromeDevTools/chrome-devtools-mcp)

---

**Integration Status:** ✅ Fully integrated with LeadFactory California

The Facebook scraper runs as a microservice alongside your main Python application, automatically providing additional high-quality leads from Facebook groups.
