#!/usr/bin/env node
/*
  Facebook Accessibility Snapshot Parser

  Input: Accessibility snapshot JSON from chrome-devtools-mcp take_snapshot tool
  Output: Tab-delimited rows suitable for Google Sheets

  Rows:
    POST	<post_id>	<author>	<timestamp>	<reactions>	<comments>	<badge>	<content>
    COMMENT	<post_id>	<author>	<time>				<content>

  Usage:
    node scripts/parse_facebook_snapshot.js snapshot.json > facebook.tsv
    cat snapshot.json | node scripts/parse_facebook_snapshot.js > facebook.tsv
*/

import fs from 'fs';
import readline from 'readline';

function readAllStdin() {
  return new Promise((resolve, reject) => {
    let data = '';
    const rl = readline.createInterface({ input: process.stdin });
    rl.on('line', line => { data += line + '\n'; });
    rl.on('close', () => resolve(data));
    rl.on('error', reject);
  });
}

async function loadSnapshot() {
  const arg = process.argv[2];
  if (!arg || arg === '-') {
    const input = await readAllStdin();
    if (!input.trim()) {
      console.error('No input provided. Pass a file path or pipe JSON via stdin.');
      process.exit(1);
    }
    return JSON.parse(input);
  }
  const json = fs.readFileSync(arg, 'utf8');
  return JSON.parse(json);
}

function getNodeRole(node) {
  return node.role || node.type || '';
}

function getNodeName(node) {
  return node.name || node.text || node.value || '';
}

function getHeadingLevel(node) {
  return node.level ?? node.headingLevel ?? node.levelValue ?? null;
}

function flattenTree(root) {
  const flat = [];
  const stack = [{ node: root, depth: 0, parentIndex: -1 }];
  while (stack.length) {
    const { node, depth, parentIndex } = stack.pop();
    const index = flat.length;
    const entry = {
      index,
      depth,
      parentIndex,
      role: getNodeRole(node),
      name: getNodeName(node),
      level: getHeadingLevel(node),
      raw: node
    };
    flat.push(entry);
    const children = node.children || [];
    for (let i = children.length - 1; i >= 0; i--) {
      stack.push({ node: children[i], depth: depth + 1, parentIndex: index });
    }
  }
  return flat;
}

function sliceBetweenHeadings(flat, startIdx) {
  const start = startIdx;
  let end = flat.length;
  for (let i = startIdx + 1; i < flat.length; i++) {
    const r = flat[i];
    if ((r.role === 'heading' || r.role === 'Heading' || r.role === 'HEADING' || r.role === 'heading level') && (r.level === 3 || r.name?.includes('level="3"'))) {
      end = i;
      break;
    }
    // Some snapshots encode as type 'heading' and numeric level
    if (r.role === 'heading' && r.level === 3) {
      end = i;
      break;
    }
  }
  return { start, end };
}

function textIsTimestamp(text) {
  if (!text) return false;
  const t = text.toLowerCase();
  return (
    t.includes('minutes ago') ||
    t.includes('minute ago') ||
    t.includes('hours ago') ||
    t.includes('hour ago') ||
    /^\d+\s*m$/i.test(t) ||
    /^\d+\s*h$/i.test(t) ||
    /\b\d+\s*(m|h)\b/i.test(t)
  );
}

function parseNumberFrom(text) {
  if (!text) return 0;
  const match = String(text).replaceAll(',', '').match(/\b(\d{1,6})\b/);
  return match ? Number(match[1]) : 0;
}

function findBadges(slice) {
  const badges = [];
  for (const r of slice) {
    const n = (r.name || '').trim();
    if (n === 'Admin' || n === 'Top contributor' || n === 'All-star contributor' || n === 'Moderator') badges.push(n);
    if (/Verified/i.test(n)) badges.push('Verified');
  }
  return Array.from(new Set(badges)).join(', ');
}

function extractPostContent(slice) {
  const texts = [];
  for (const r of slice) {
    const role = (r.role || '').toLowerCase();
    const name = (r.name || '').trim();
    if (role === 'button') {
      // Stop before meta buttons section
      if (/comments?/i.test(name) || /like/i.test(name) || /all reactions/i.test(name)) break;
    }
    if (role === 'statictext' || role === 'text' || role === 'label' || role === 'textbox') {
      // Exclude boilerplate
      if (!name) continue;
      if (/^like:?/i.test(name)) continue;
      if (/^comment/i.test(name)) continue;
      if (/^share/i.test(name)) continue;
      if (/^view more/i.test(name)) continue;
      if (textIsTimestamp(name)) continue;
      texts.push(name);
    }
  }
  const joined = texts.join(' ').replace(/\s+/g, ' ').trim();
  return joined;
}

function extractTimestamp(slice) {
  for (const r of slice) {
    const role = (r.role || '').toLowerCase();
    if (role === 'link' && textIsTimestamp(r.name)) return r.name;
  }
  return '';
}

function extractReactions(slice) {
  let reactions = 0;
  for (const r of slice) {
    const role = (r.role || '').toLowerCase();
    const name = (r.name || '').toLowerCase();
    if (role === 'button' && (name.includes('like:') || name.includes('all reactions'))) {
      const n = parseNumberFrom(r.name);
      reactions = Math.max(reactions, n);
    }
  }
  return reactions;
}

function extractCommentCount(slice) {
  for (const r of slice) {
    const role = (r.role || '').toLowerCase();
    const name = (r.name || '').toLowerCase();
    if (role === 'button' && name.includes('comment')) {
      return parseNumberFrom(r.name);
    }
  }
  return 0;
}

function extractComments(slice) {
  const comments = [];
  for (let i = 0; i < slice.length; i++) {
    const r = slice[i];
    const role = (r.role || '').toLowerCase();
    const name = (r.name || '').trim();
    if (role === 'article' && /comment by/i.test(name)) {
      // Scan descendants forward until next article/heading/button cluster
      const seg = [];
      for (let j = i + 1; j < slice.length; j++) {
        const rr = slice[j];
        if ((rr.role || '').toLowerCase() === 'article' || ((rr.role || '').toLowerCase() === 'heading' && (rr.level === 3))) break;
        seg.push(rr);
      }
      const author = (() => {
        for (const rr of seg) if ((rr.role || '').toLowerCase() === 'link' && rr.name?.trim()) return rr.name.trim();
        return '';
      })();
      const time = (() => {
        for (const rr of seg) if ((rr.role || '').toLowerCase() === 'link' && textIsTimestamp(rr.name)) return rr.name.trim();
        return '';
      })();
      const content = (() => {
        const txts = [];
        for (const rr of seg) {
          const rrole = (rr.role || '').toLowerCase();
          if (rrole === 'statictext' || rrole === 'text' || rrole === 'label') {
            const t = (rr.name || '').trim();
            if (!t) continue;
            if (textIsTimestamp(t)) continue;
            if (/^like$/i.test(t)) continue;
            txts.push(t);
          }
        }
        return txts.join(' ').replace(/\s+/g, ' ').trim();
      })();
      comments.push({ author, time, content });
    }
  }
  return comments;
}

function sanitizeField(value) {
  return String(value ?? '').replaceAll('\t', ' ').replaceAll('\n', ' ').replace(/\s+/g, ' ').trim();
}

function normalizeName(name) {
  return String(name || '').replace(/\s+/g, ' ').trim().toLowerCase();
}

function loadProfilesMap() {
  try {
    const arg = (process.argv || []).find(a => a && a.startsWith('--profiles='));
    if (!arg) return null;
    const file = arg.split('=')[1];
    if (!file) return null;
    const raw = fs.readFileSync(file, 'utf8');
    const json = JSON.parse(raw);
    const map = new Map();
    const add = (arr) => {
      if (!Array.isArray(arr)) return;
      for (const e of arr) {
        const key = normalizeName(e?.author);
        const url = e?.authorUrl || e?.url || e?.href || '';
        if (key && url && !map.has(key)) map.set(key, url);
      }
    };
    add(json.posts);
    add(json.comments);
    return map;
  } catch {
    return null;
  }
}

async function main() {
  const snapshot = await loadSnapshot();
  const profilesMap = loadProfilesMap();
  // Some MCP clients wrap the tree, others return a list; try to normalize
  const root = snapshot.root || snapshot.tree || snapshot;
  const flat = Array.isArray(root) ? root.flatMap(n => flattenTree(n)) : flattenTree(root);

  // Identify post headers
  const postHeaderIdxs = [];
  for (let i = 0; i < flat.length; i++) {
    const r = flat[i];
    const isHeading = (r.role || '').toLowerCase() === 'heading' || (r.role || '').toLowerCase() === 'heading level' || (r.raw?.role === 'heading');
    const levelOk = r.level === 3 || /level\s*=?\s*"?3"?/i.test(r.name || '');
    if (isHeading && levelOk) postHeaderIdxs.push(i);
  }

  let postCounter = 0;
  for (let h = 0; h < postHeaderIdxs.length; h++) {
    const startIdx = postHeaderIdxs[h];
    const { end } = sliceBetweenHeadings(flat, startIdx);
    const slice = flat.slice(startIdx, end);
    const header = flat[startIdx];

    // Author: header name or first static text under header
    let author = sanitizeField(header.name);
    if (!author) {
      for (const r of slice) {
        if ((r.role || '').toLowerCase() === 'statictext' && r.name?.trim()) { author = sanitizeField(r.name); break; }
      }
    }

    const timestamp = sanitizeField(extractTimestamp(slice));
    const content = sanitizeField(extractPostContent(slice));
    const reactions = extractReactions(slice);
    const commentCount = extractCommentCount(slice);
    const badge = sanitizeField(findBadges(slice));

    const postId = `P${++postCounter}`;
    const authorUrl = profilesMap ? (profilesMap.get(normalizeName(author)) || '') : '';
    const postRow = [
      'POST', postId, author, authorUrl, timestamp, reactions, commentCount, badge, content
    ].map(sanitizeField).join('\t');
    console.log(postRow);

    // Comments
    const comments = extractComments(slice);
    for (const c of comments) {
      const cAuthor = sanitizeField(c.author);
      const cUrl = profilesMap ? (profilesMap.get(normalizeName(cAuthor)) || '') : '';
      const row = [
        'COMMENT', postId, cAuthor, cUrl, sanitizeField(c.time), '', '', '', sanitizeField(c.content)
      ].join('\t');
      console.log(row);
    }
  }
}

main().catch(err => {
  console.error('Error:', err?.stack || err?.message || err);
  process.exit(1);
});


