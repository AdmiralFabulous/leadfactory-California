### Facebook Group Extraction via Chrome DevTools MCP

This project uses the Chrome DevTools MCP server to navigate a Facebook group, take an accessibility-tree snapshot, and parse it into TSV for Google Sheets. See Chrome DevTools MCP docs: [chrome-devtools-mcp](https://github.com/ChromeDevTools/chrome-devtools-mcp).

#### Prerequisites
- Node.js 22.12.0 or newer (required by chrome-devtools-mcp)
- Cursor with MCP enabled

Check your Node version:
```bash
node -v
```
If lower than 22.12.0, upgrade Node (e.g., via nvm-windows) before proceeding.

#### 1) Configure MCP in Cursor
File: `.cursor/mcp.json`
```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": [
        "chrome-devtools-mcp@latest",
        "--isolated=true"
      ]
    }
  }
}
```
Then in Cursor: Settings → MCP → ensure `chrome-devtools` is enabled.

#### 2) Open browser and capture snapshot
In Cursor chat, run these tools (Chrome will launch automatically):
- `chrome-devtools:navigate_page` with `{ "url": "https://www.facebook.com/groups/epicretire" }`
- Optional: `chrome-devtools:evaluate_script` with `{ "function": "() => { window.scrollBy(0, 1500); return 'Scrolled'; }" }` to load more posts
- `chrome-devtools:take_snapshot` with `{}` to get the accessibility tree JSON

Copy the JSON result into a file like `snapshots/fb-group-1.json`.

#### 3) Enrich with profile URLs (recommended)
Use `chrome-devtools:evaluate_script` to extract profile anchors (author names link to profiles). Run this on the group page before taking the snapshot:

```json
{
  "function": "() => {\n  const toAbs = (u) => { try { return new URL(u, location.href).href; } catch { return ''; } };\n  const posts = [];\n  document.querySelectorAll('h3').forEach((h, idx) => {\n    const authorLink = h.closest('*')?.querySelector('a[role=link], a[tabindex]');\n    if (authorLink && authorLink.textContent) {\n      posts.push({ idx, author: authorLink.textContent.trim(), authorUrl: toAbs(authorLink.getAttribute('href') || '') });\n    }\n  });\n  const comments = [];\n  document.querySelectorAll('[role=article] a[role=link], [role=article] a').forEach(a => {\n    const name = a.textContent?.trim();\n    const href = toAbs(a.getAttribute('href') || '');\n    if (name && href && /facebook\\.com\//.test(href)) { comments.push({ author: name, authorUrl: href }); }\n  });\n  return { posts, comments };\n}"
}
```

Save the returned JSON alongside your snapshot (e.g., `snapshots/fb-profiles.json`). This helps map exact profile URLs for authors and commenters even when the accessibility snapshot only has names.

#### 4) Parse snapshot to TSV
Scripts:
- `scripts/parse_facebook_snapshot.js` — parses posts and comments from the snapshot

Run:
```bash
node scripts/parse_facebook_snapshot.js snapshots/fb-group-1.json > out/facebook.tsv
```
Or pipe from stdin:
```bash
cat snapshots/fb-group-1.json | node scripts/parse_facebook_snapshot.js > out/facebook.tsv
```

Output format (tab-delimited):
- POST	post_id	author	author_url	timestamp	reactions	comments	badge	content
- COMMENT	post_id	author	author_url	time				content

#### 5) Export JSON to CSV
If you have a single JSON with `posts`, `comments`, and `summary`, run:

```bash
node scripts/export_fb_json_to_csv.js exports/epicretire.json
```

This writes 4 CSVs in `exports/` and a combined file.

#### Notes
- The parser relies on common Facebook accessibility patterns: level-3 headings for post headers, nearby links for timestamps, buttons for reactions and comment counts, and articles for comments.
- If Facebook structure changes, adjust selectors/heuristics in `scripts/parse_facebook_snapshot.js`.

Reference: [Chrome DevTools MCP](https://github.com/ChromeDevTools/chrome-devtools-mcp)


