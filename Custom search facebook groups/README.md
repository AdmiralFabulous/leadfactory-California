# Facebook Group Scraper → Google Sheets (Sim workflow)

A Sim (beflow) workflow that fetches Facebook group members and writes their profile info to a Google Sheets tab.

## Files
- `facebook-group-scraper.yaml` — ready-to-import Sim YAML
- `facebook-retire-scraper.yaml` — Sim YAML to collect retirement-related posts + comments via Chrome DevTools MCP and write to Sheets
- `scraper-design` — design notes and rationale

## Required environment variables
Set these in Sim (Workspace → Settings → Environment Variables):

- `GROUP_ID`: Facebook Group ID (numeric)
- `GROUP_ID_OR_PATH`: Group path or ID used by the retire scraper (e.g., `epicretire` or a numeric ID)
- `FB_ACCESS_TOKEN`: Graph API token with Groups access (e.g., `groups_access_member_info`)
- `SHEET_ID`: Google Sheets spreadsheet ID
- `GOOGLE_SHEETS_TOKEN`: OAuth Bearer token for Google Sheets API

Notes:
- Graph API typically returns `id`, `name`, `link` for group members. Email for other users is generally not available and will be left blank in the sheet.
- The YAML schedules daily runs at 09:00 UTC. Adjust in the `start` block as needed.

## Import & run
1. In Sim, create a new workflow and paste the contents of `facebook-group-scraper.yaml`.
2. Ensure the target spreadsheet has a tab/range `Sheet1!A:D` (or change the range in the YAML).
3. Manual test: Run once from the editor and confirm rows appear in the sheet.
4. Deploy/schedule as desired.

### Retire posts scraper (MCP)
1. Ensure Cursor’s MCP has `chrome-devtools` configured in `.cursor/mcp.json` as:
   ```json
   {"mcpServers":{"chrome-devtools":{"command":"npx","args":["-y","--package=chrome-devtools-mcp@latest","chrome-devtools-mcp"]}}}
   ```
2. In Sim, create a new workflow and paste `facebook-retire-scraper.yaml`.
3. Set envs: `GROUP_ID_OR_PATH`, `SHEET_ID`, `GOOGLE_SHEETS_TOKEN`, `OPENAI_API_KEY`.
4. Run manually; it will open the group, expand, extract rows, and write to `Sheet1!A:G`.

## Limitations & next steps
- Pagination: The members endpoint paginates results. This initial version fetches the first page (`limit=200`). Extend by iterating `paging.next` until exhausted.
- Interactions (commenters/reactors): Not included. Implement additional calls (e.g., group feed + comments/likes) if your app permissions allow access.
- Rate limits: Consider Parallel blocks and backoff if scaling.

## Security
- Store tokens only in Sim env vars. Rotate regularly. Avoid committing secrets to source control.
