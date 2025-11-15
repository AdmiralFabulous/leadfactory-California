#!/usr/bin/env node
/**
 * Test CSV export functionality with Epic Retire group data
 */

import { CSVExporter } from './server/csv-exporter.js';

async function testCSVExport() {
  console.log('📊 Testing CSV Export for Epic Retire Group');
  console.log('═'.repeat(60));
  
  // Mock data similar to what would be scraped from Epic Retire group
  const mockData = {
    posts: [
      {
        id: 'P1',
        author: 'John Smith',
        authorUrl: 'https://facebook.com/profile/john.smith',
        content: 'Just retired after 30 years in tech! Looking forward to traveling and exploring new hobbies. Any recommendations for retirement destinations?',
        timestamp: '2h',
        reactions: 15,
        commentCount: 3,
        badge: 'Top contributor'
      },
      {
        id: 'P2',
        author: 'Sarah Johnson',
        authorUrl: 'https://facebook.com/profile/sarah.johnson',
        content: 'Healthcare costs are really concerning me. Has anyone found good strategies for managing medical expenses in retirement?',
        timestamp: '4h',
        reactions: 23,
        commentCount: 7,
        badge: ''
      },
      {
        id: 'P3',
        author: 'Mike Wilson',
        authorUrl: 'https://facebook.com/profile/mike.wilson',
        content: 'Loving my new hobby of gardening! Started a vegetable garden and it\'s so rewarding. Plus it helps with the grocery budget.',
        timestamp: '6h',
        reactions: 12,
        commentCount: 2,
        badge: 'All-star contributor'
      }
    ],
    comments: [
      {
        postId: 'P1',
        author: 'Lisa Brown',
        authorUrl: 'https://facebook.com/profile/lisa.brown',
        content: 'Congratulations on your retirement! I highly recommend Costa Rica - beautiful and affordable.',
        timestamp: '1h'
      },
      {
        postId: 'P1',
        author: 'David Lee',
        authorUrl: 'https://facebook.com/profile/david.lee',
        content: 'Portugal is amazing too! Great weather and very retiree-friendly.',
        timestamp: '45m'
      },
      {
        postId: 'P2',
        author: 'Emma Davis',
        authorUrl: 'https://facebook.com/profile/emma.davis',
        content: 'Look into Medicare Advantage plans. They can really help with costs.',
        timestamp: '3h'
      },
      {
        postId: 'P2',
        author: 'Robert Jones',
        authorUrl: 'https://facebook.com/profile/robert.jones',
        content: 'HSA accounts are great for medical expenses if you still have access to one.',
        timestamp: '2h'
      }
    ],
    profiles: [
      'https://facebook.com/profile/john.smith',
      'https://facebook.com/profile/sarah.johnson',
      'https://facebook.com/profile/mike.wilson',
      'https://facebook.com/profile/lisa.brown',
      'https://facebook.com/profile/david.lee',
      'https://facebook.com/profile/emma.davis',
      'https://facebook.com/profile/robert.jones'
    ],
    summary: {
      totalPosts: 3,
      totalComments: 4,
      uniqueProfiles: 7,
      scrapedAt: new Date().toISOString()
    }
  };
  
  try {
    const csvExporter = new CSVExporter();
    
    console.log('🚀 Starting CSV export...\n');
    
    // Export individual CSV files
    const csvFiles = await csvExporter.exportData(mockData, 'epicretire-test');
    
    console.log('\n📁 Individual CSV files created:');
    console.log(`   📝 Posts: ${csvFiles.posts}`);
    console.log(`   💬 Comments: ${csvFiles.comments}`);
    console.log(`   👤 Profiles: ${csvFiles.profiles}`);
    console.log(`   📊 Summary: ${csvFiles.summary}`);
    
    // Export combined CSV
    console.log('\n🔗 Creating combined CSV...');
    const combinedFile = await csvExporter.exportCombinedCSV(mockData, 'epicretire-combined-test');
    console.log(`   📋 Combined: ${combinedFile}`);
    
    console.log('\n✅ CSV Export Test Complete!');
    console.log('\n📋 Sample CSV Content Preview:');
    console.log('─'.repeat(50));
    
    // Show sample of posts CSV content
    const fs = await import('fs');
    const postsContent = fs.default.readFileSync(csvFiles.posts, 'utf8');
    const lines = postsContent.split('\n');
    
    console.log('📝 Posts CSV (first 3 lines):');
    lines.slice(0, 3).forEach((line, i) => {
      console.log(`   ${i + 1}: ${line}`);
    });
    
    console.log('\n🎯 Ready for real scraping!');
    console.log('The CSV export system is working correctly.');
    console.log('When you run the real scraper, CSV files will be automatically created.');
    
  } catch (error) {
    console.error('❌ CSV Export Test Failed:', error.message);
  }
}

testCSVExport().catch(console.error);
