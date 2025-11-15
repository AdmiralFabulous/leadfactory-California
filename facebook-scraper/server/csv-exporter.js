import fs from 'fs';
import path from 'path';

export class CSVExporter {
  constructor() {
    this.outputDir = 'exports';
    this.ensureOutputDir();
  }

  ensureOutputDir() {
    if (!fs.existsSync(this.outputDir)) {
      fs.mkdirSync(this.outputDir, { recursive: true });
    }
  }

  escapeCSVField(field) {
    if (field === null || field === undefined) return '';
    const str = String(field);
    // Escape quotes by doubling them and wrap in quotes if contains comma, quote, or newline
    if (str.includes(',') || str.includes('"') || str.includes('\n') || str.includes('\r')) {
      return '"' + str.replace(/"/g, '""') + '"';
    }
    return str;
  }

  arrayToCSV(headers, rows) {
    const csvHeaders = headers.map(h => this.escapeCSVField(h)).join(',');
    const csvRows = rows.map(row => 
      row.map(field => this.escapeCSVField(field)).join(',')
    );
    return [csvHeaders, ...csvRows].join('\n');
  }

  async exportData(data, filename = null) {
    try {
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
      const baseFilename = filename || `facebook-group-${timestamp}`;
      
      // Posts CSV
      const postsHeaders = [
        'Post ID', 'Author', 'Author URL', 'Content', 'Timestamp', 
        'Reactions', 'Comment Count', 'Badge', 'Scraped At'
      ];
      
      const postsRows = data.posts.map(post => [
        post.id,
        post.author,
        post.authorUrl,
        post.content,
        post.timestamp,
        post.reactions,
        post.commentCount,
        post.badge,
        data.summary.scrapedAt
      ]);
      
      const postsCSV = this.arrayToCSV(postsHeaders, postsRows);
      const postsFile = path.join(this.outputDir, `${baseFilename}-posts.csv`);
      fs.writeFileSync(postsFile, postsCSV, 'utf8');
      
      // Comments CSV
      const commentsHeaders = [
        'Post ID', 'Author', 'Author URL', 'Content', 'Timestamp', 'Scraped At'
      ];
      
      const commentsRows = data.comments.map(comment => [
        comment.postId,
        comment.author,
        comment.authorUrl,
        comment.content,
        comment.timestamp,
        data.summary.scrapedAt
      ]);
      
      const commentsCSV = this.arrayToCSV(commentsHeaders, commentsRows);
      const commentsFile = path.join(this.outputDir, `${baseFilename}-comments.csv`);
      fs.writeFileSync(commentsFile, commentsCSV, 'utf8');
      
      // Profiles CSV
      const profilesHeaders = ['Profile URL', 'First Seen', 'Type'];
      const profilesRows = data.profiles.map(profileUrl => {
        const isPostAuthor = data.posts.some(post => post.authorUrl === profileUrl);
        const isCommentAuthor = data.comments.some(comment => comment.authorUrl === profileUrl);
        
        let type = '';
        if (isPostAuthor && isCommentAuthor) type = 'Post & Comment Author';
        else if (isPostAuthor) type = 'Post Author';
        else if (isCommentAuthor) type = 'Comment Author';
        
        return [
          profileUrl,
          data.summary.scrapedAt,
          type
        ];
      });
      
      const profilesCSV = this.arrayToCSV(profilesHeaders, profilesRows);
      const profilesFile = path.join(this.outputDir, `${baseFilename}-profiles.csv`);
      fs.writeFileSync(profilesFile, profilesCSV, 'utf8');
      
      // Combined summary CSV
      const summaryHeaders = [
        'Metric', 'Value', 'Scraped At', 'Group URL'
      ];
      
      const summaryRows = [
        ['Total Posts', data.summary.totalPosts, data.summary.scrapedAt, 'https://www.facebook.com/groups/epicretire'],
        ['Total Comments', data.summary.totalComments, data.summary.scrapedAt, 'https://www.facebook.com/groups/epicretire'],
        ['Unique Profiles', data.summary.uniqueProfiles, data.summary.scrapedAt, 'https://www.facebook.com/groups/epicretire']
      ];
      
      const summaryCSV = this.arrayToCSV(summaryHeaders, summaryRows);
      const summaryFile = path.join(this.outputDir, `${baseFilename}-summary.csv`);
      fs.writeFileSync(summaryFile, summaryCSV, 'utf8');
      
      console.log('✅ CSV files exported successfully:');
      console.log(`   📝 Posts: ${postsFile}`);
      console.log(`   💬 Comments: ${commentsFile}`);
      console.log(`   👤 Profiles: ${profilesFile}`);
      console.log(`   📊 Summary: ${summaryFile}`);
      
      return {
        posts: postsFile,
        comments: commentsFile,
        profiles: profilesFile,
        summary: summaryFile,
        baseFilename
      };
      
    } catch (error) {
      console.error('❌ CSV export failed:', error);
      throw new Error(`CSV export failed: ${error.message}`);
    }
  }

  // Generate a single combined CSV with all data
  async exportCombinedCSV(data, filename = null) {
    try {
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
      const baseFilename = filename || `facebook-group-combined-${timestamp}`;
      
      const headers = [
        'Type', 'Post ID', 'Author', 'Author URL', 'Content', 'Timestamp',
        'Reactions', 'Comment Count', 'Badge', 'Parent Post', 'Scraped At'
      ];
      
      const rows = [];
      
      // Add posts
      data.posts.forEach(post => {
        rows.push([
          'POST',
          post.id,
          post.author,
          post.authorUrl,
          post.content,
          post.timestamp,
          post.reactions,
          post.commentCount,
          post.badge,
          '', // No parent post for posts
          data.summary.scrapedAt
        ]);
      });
      
      // Add comments
      data.comments.forEach(comment => {
        rows.push([
          'COMMENT',
          '', // Comments don't have their own ID
          comment.author,
          comment.authorUrl,
          comment.content,
          comment.timestamp,
          '', // Comments don't have reactions in this format
          '', // Comments don't have comment counts
          '', // Comments don't have badges
          comment.postId, // Parent post ID
          data.summary.scrapedAt
        ]);
      });
      
      const combinedCSV = this.arrayToCSV(headers, rows);
      const combinedFile = path.join(this.outputDir, `${baseFilename}.csv`);
      fs.writeFileSync(combinedFile, combinedCSV, 'utf8');
      
      console.log(`✅ Combined CSV exported: ${combinedFile}`);
      
      return combinedFile;
      
    } catch (error) {
      console.error('❌ Combined CSV export failed:', error);
      throw new Error(`Combined CSV export failed: ${error.message}`);
    }
  }
}
