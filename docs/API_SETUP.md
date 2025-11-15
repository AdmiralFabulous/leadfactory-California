# API Setup Guide

This guide walks you through setting up all required API integrations.

## Required APIs

### 1. Anthropic Claude API (Required)

**Purpose:** Powers all AI agents

**Setup:**
1. Go to https://console.anthropic.com/
2. Sign up / Sign in
3. Go to API Keys
4. Create new key
5. Copy the key (starts with `sk-ant-`)

**Add to `.env`:**
```bash
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

**Cost:** Pay-as-you-go
- Claude Sonnet 4.5: ~$3/million input tokens, ~$15/million output tokens
- Estimated: $50-200/month for 100 leads/day

---

### 2. Google APIs (Gmail + Calendar) - Required for Email & Booking

**Purpose:** Send emails, book Google Meet calls

**Setup:**

#### Step 1: Create Google Cloud Project

1. Go to https://console.cloud.google.com/
2. Create new project: "LeadFactory California"
3. Enable APIs:
   - Go to "APIs & Services" → "Library"
   - Enable "Gmail API"
   - Enable "Google Calendar API"

#### Step 2: Create OAuth Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. If prompted, configure consent screen:
   - User Type: External
   - App name: "LeadFactory California"
   - Support email: your email
   - Scopes: Add Gmail and Calendar scopes (we'll handle in code)
   - Test users: Add your Gmail address
4. Application type: "Desktop app"
5. Name: "LeadFactory Desktop"
6. Click "Create"
7. Note down:
   - Client ID
   - Client Secret

#### Step 3: Get Refresh Token

Run the setup script:

```bash
python scripts/setup_google_auth.py
```

This will:
- Prompt for Client ID and Secret
- Open browser for OAuth flow
- Get your refresh token
- Optionally update `.env` automatically

**Manual `.env` entry:**
```bash
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-secret
GOOGLE_REFRESH_TOKEN=your-refresh-token
GMAIL_SENDER_EMAIL=your-email@gmail.com
GMAIL_SENDER_NAME=Your Name
```

**Cost:** Free (within generous quota)

---

### 3. Reddit API (Recommended)

**Purpose:** Find leads in subreddits

**Setup:**

1. Go to https://www.reddit.com/prefs/apps
2. Click "Create App" or "Create Another App"
3. Fill in:
   - Name: "LeadFactory California"
   - App type: "script"
   - Description: "Lead generation for residency consulting"
   - About URL: (leave blank)
   - Redirect URI: `http://localhost:8080`
4. Click "Create app"
5. Note down:
   - Client ID (under the app name, small text)
   - Client Secret

**Add to `.env`:**
```bash
REDDIT_CLIENT_ID=your-client-id
REDDIT_CLIENT_SECRET=your-secret
REDDIT_USER_AGENT=LeadFactoryBot/1.0 by YourRedditUsername
```

**Cost:** Free

**Limits:**
- 60 requests/minute
- Respect subreddit rules
- Don't spam DMs

---

## Optional APIs

### 4. Google Custom Search (Optional - for web searches)

**Purpose:** Find leads via Google search

**Setup:**

1. Go to https://console.cloud.google.com/apis/credentials
2. Create API Key
3. Enable "Custom Search API"
4. Create Custom Search Engine:
   - Go to https://programmablesearchengine.google.com/
   - Create new search engine
   - Search the entire web
   - Note the Search Engine ID

**Add to `.env`:**
```bash
GOOGLE_SEARCH_API_KEY=your-api-key
GOOGLE_SEARCH_ENGINE_ID=your-search-engine-id
```

**Cost:**
- Free tier: 100 queries/day
- Paid: $5 per 1000 queries

---

### 5. LinkedIn API (Optional - very limited)

**Note:** LinkedIn severely restricts API access. Only available to partners.

**Alternatives:**
- Manual outreach via LinkedIn
- Browser automation (against ToS, risky)
- Use email/Reddit instead

We recommend focusing on Reddit and email for MVP.

---

### 6. People Enrichment APIs (Optional)

To find email addresses from names/usernames:

**Apollo.io:**
- https://www.apollo.io/
- $49-99/month for 1000+ credits
- Good for B2B enrichment

**Hunter.io:**
- https://hunter.io/
- Free tier: 25 searches/month
- $49/month for 500 searches

**Clearbit:**
- https://clearbit.com/
- Enterprise pricing
- Best quality, but expensive

**Setup:**
Add to `.env`:
```bash
APOLLO_API_KEY=your-key
HUNTER_API_KEY=your-key
CLEARBIT_API_KEY=your-key
```

For MVP, we use web search (free) for enrichment.
Add paid APIs later for better conversion.

---

## Testing Your Setup

After configuring APIs, run:

```bash
# Initialize database
python -m database.init_db

# Load knowledge base
python -m services.knowledge_base_loader

# Test APIs
python main.py --mode test
```

Expected output:
```
✓ Database working
✓ Claude API working
✓ Knowledge base working
✓ Google APIs working (if configured)
✓ Reddit API working (if configured)
```

---

## Troubleshooting

### "ANTHROPIC_API_KEY not set"

Make sure you copied `.env.example` to `.env` and added your key.

### "Google authentication failed"

1. Make sure OAuth consent screen is configured
2. Add your email as a test user
3. Re-run `python scripts/setup_google_auth.py`

### "Reddit API error"

1. Check client ID and secret are correct
2. Ensure user agent string is unique
3. Check you're not hitting rate limits

### "Gmail quota exceeded"

Gmail API has daily limits:
- Free: 100-500 emails/day (varies)
- Google Workspace: Higher limits

Solution: Use a transactional email service (SendGrid, Mailgun) for higher volume.

---

## Security Best Practices

1. **Never commit `.env`** - It's in `.gitignore`
2. **Rotate API keys** regularly
3. **Use separate Gmail account** - Don't use personal email
4. **Monitor API usage** - Set up billing alerts
5. **Restrict API keys** - Use IP restrictions where possible

---

## Cost Estimate

**Minimum (MVP with free tiers):**
- Anthropic Claude: $50-100/month
- Google APIs: Free
- Reddit: Free
- **Total: ~$50-100/month**

**Recommended (with enrichment):**
- Anthropic Claude: $100-200/month
- Google APIs: Free
- Reddit: Free
- Apollo/Hunter: $49-99/month
- **Total: ~$150-300/month**

**Scale (1000+ leads/day):**
- Claude: $500-1000/month
- Google Workspace: $6-12/user/month
- Enrichment: $200-500/month
- Infrastructure: $50-100/month
- **Total: ~$750-1600/month**

All costs scale with usage. Start with MVP, add paid features as you see ROI.
