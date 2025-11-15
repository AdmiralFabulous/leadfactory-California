#!/usr/bin/env node
/*
  Export Facebook JSON (posts/comments with author URLs) to CSV files.

  Input JSON structure expected:
  {
    posts: [
      { id, author, authorUrl, content, timestamp, reactions, commentCount, badge }
    ],
    comments: [
      { postId, author, authorUrl, content, timestamp }
    ],
    summary?: { scrapedAt?: string }
  }

  Usage (PowerShell / bash):
    node scripts/export_fb_json_to_csv.js exports/epicretire.json

  Output:
    - exports/<base>-posts.csv
    - exports/<base>-comments.csv
    - exports/<base>-profiles.csv
    - exports/<base>-summary.csv
    - exports/<base>-combined.csv
*/

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { CSVExporter } from '../server/csv-exporter.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function readJson(filePath) {
  const abs = path.isAbsolute(filePath) ? filePath : path.join(process.cwd(), filePath);
  const raw = fs.readFileSync(abs, 'utf8');
  return JSON.parse(raw);
}

function ensureSummary(data) {
  const scrapedAt = data?.summary?.scrapedAt || new Date().toISOString();
  const totalPosts = Array.isArray(data.posts) ? data.posts.length : 0;
  const totalComments = Array.isArray(data.comments) ? data.comments.length : 0;
  const uniqueProfiles = new Set([
    ...(data.posts?.map(p => p.authorUrl) || []),
    ...(data.comments?.map(c => c.authorUrl) || [])
  ].filter(Boolean)).size;
  return {
    ...data,
    profiles: Array.from(new Set([
      ...(data.posts?.map(p => p.authorUrl) || []),
      ...(data.comments?.map(c => c.authorUrl) || [])
    ].filter(Boolean))),
    summary: { scrapedAt, totalPosts, totalComments, uniqueProfiles }
  };
}

function deriveBaseFilename(inputPath) {
  const base = path.basename(inputPath).replace(/\.json$/i, '');
  return base || 'facebook-group';
}

async function main() {
  const input = process.argv[2];
  if (!input) {
    console.error('Usage: node scripts/export_fb_json_to_csv.js <input.json>');
    process.exit(1);
  }

  const json = readJson(input);
  const data = ensureSummary(json);
  const exporter = new CSVExporter();
  const baseFilename = deriveBaseFilename(input);

  const files = await exporter.exportData(data, baseFilename);
  await exporter.exportCombinedCSV(data, `${baseFilename}-combined`);

  console.log('CSV export complete.');
  console.log(files);
}

main().catch(err => {
  console.error('Export failed:', err?.stack || err?.message || err);
  process.exit(1);
});



