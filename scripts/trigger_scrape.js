#!/usr/bin/env node
// Trigger the local scraper server to scrape the Epic Retire group

const url = 'http://localhost:3001/api/scrape';

async function main() {
  try {
    const resp = await fetch(url, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        url: 'https://www.facebook.com/groups/epicretire',
        exportToSheets: false,
        exportToCSV: true
      })
    });
    const text = await resp.text();
    console.log(text);
  } catch (err) {
    console.error('Trigger failed:', err?.message || err);
    process.exit(1);
  }
}

main();



