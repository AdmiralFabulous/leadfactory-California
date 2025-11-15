import { google } from 'googleapis';
import fs from 'fs';
import path from 'path';

export class GoogleSheetsExporter {
  constructor() {
    this.auth = null;
    this.sheets = null;
  }

  async authenticate() {
    try {
      // Try to load service account credentials
      const credentialsPath = process.env.GOOGLE_CREDENTIALS_PATH || 'credentials.json';
      
      if (fs.existsSync(credentialsPath)) {
        const credentials = JSON.parse(fs.readFileSync(credentialsPath, 'utf8'));
        
        this.auth = new google.auth.GoogleAuth({
          credentials,
          scopes: ['https://www.googleapis.com/auth/spreadsheets']
        });
      } else {
        // Fallback to environment variable
        const credentials = process.env.GOOGLE_CREDENTIALS;
        if (credentials) {
          this.auth = new google.auth.GoogleAuth({
            credentials: JSON.parse(credentials),
            scopes: ['https://www.googleapis.com/auth/spreadsheets']
          });
        } else {
          throw new Error('Google credentials not found. Please set GOOGLE_CREDENTIALS_PATH or GOOGLE_CREDENTIALS environment variable.');
        }
      }
      
      this.sheets = google.sheets({ version: 'v4', auth: this.auth });
      return true;
    } catch (error) {
      console.error('Google Sheets authentication failed:', error);
      throw new Error('Failed to authenticate with Google Sheets API');
    }
  }

  async createSpreadsheet(title) {
    try {
      const response = await this.sheets.spreadsheets.create({
        resource: {
          properties: {
            title
          },
          sheets: [
            {
              properties: {
                title: 'Posts',
                gridProperties: {
                  rowCount: 1000,
                  columnCount: 10
                }
              }
            },
            {
              properties: {
                title: 'Comments',
                gridProperties: {
                  rowCount: 5000,
                  columnCount: 8
                }
              }
            },
            {
              properties: {
                title: 'Profiles',
                gridProperties: {
                  rowCount: 1000,
                  columnCount: 3
                }
              }
            }
          ]
        }
      });
      
      return response.data;
    } catch (error) {
      console.error('Failed to create spreadsheet:', error);
      throw new Error('Failed to create Google Spreadsheet');
    }
  }

  async exportData(data, title) {
    try {
      await this.authenticate();
      
      const spreadsheet = await this.createSpreadsheet(title);
      const spreadsheetId = spreadsheet.spreadsheetId;
      
      // Prepare posts data
      const postsHeaders = [
        'Post ID', 'Author', 'Author URL', 'Content', 'Timestamp', 
        'Reactions', 'Comment Count', 'Badge', 'Scraped At'
      ];
      
      const postsData = [
        postsHeaders,
        ...data.posts.map(post => [
          post.id,
          post.author,
          post.authorUrl,
          post.content,
          post.timestamp,
          post.reactions,
          post.commentCount,
          post.badge,
          data.summary.scrapedAt
        ])
      ];
      
      // Prepare comments data
      const commentsHeaders = [
        'Post ID', 'Author', 'Author URL', 'Content', 'Timestamp', 'Scraped At'
      ];
      
      const commentsData = [
        commentsHeaders,
        ...data.comments.map(comment => [
          comment.postId,
          comment.author,
          comment.authorUrl,
          comment.content,
          comment.timestamp,
          data.summary.scrapedAt
        ])
      ];
      
      // Prepare profiles data
      const profilesHeaders = ['Profile URL', 'First Seen', 'Type'];
      const profilesData = [
        profilesHeaders,
        ...data.profiles.map(profileUrl => {
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
        })
      ];
      
      // Write data to sheets
      await Promise.all([
        // Posts sheet
        this.sheets.spreadsheets.values.update({
          spreadsheetId,
          range: 'Posts!A1',
          valueInputOption: 'RAW',
          resource: {
            values: postsData
          }
        }),
        
        // Comments sheet
        this.sheets.spreadsheets.values.update({
          spreadsheetId,
          range: 'Comments!A1',
          valueInputOption: 'RAW',
          resource: {
            values: commentsData
          }
        }),
        
        // Profiles sheet
        this.sheets.spreadsheets.values.update({
          spreadsheetId,
          range: 'Profiles!A1',
          valueInputOption: 'RAW',
          resource: {
            values: profilesData
          }
        })
      ]);
      
      // Format headers
      await this.formatHeaders(spreadsheetId);
      
      // Make spreadsheet publicly viewable (optional)
      try {
        const drive = google.drive({ version: 'v3', auth: this.auth });
        await drive.permissions.create({
          fileId: spreadsheetId,
          resource: {
            role: 'reader',
            type: 'anyone'
          }
        });
      } catch (error) {
        console.warn('Could not make spreadsheet public:', error.message);
      }
      
      const sheetUrl = `https://docs.google.com/spreadsheets/d/${spreadsheetId}`;
      console.log('Data exported to Google Sheets:', sheetUrl);
      
      return sheetUrl;
      
    } catch (error) {
      console.error('Export to Google Sheets failed:', error);
      throw error;
    }
  }

  async formatHeaders(spreadsheetId) {
    try {
      const requests = [
        // Format Posts sheet header
        {
          repeatCell: {
            range: {
              sheetId: 0,
              startRowIndex: 0,
              endRowIndex: 1
            },
            cell: {
              userEnteredFormat: {
                backgroundColor: { red: 0.2, green: 0.6, blue: 1.0 },
                textFormat: { bold: true, foregroundColor: { red: 1.0, green: 1.0, blue: 1.0 } }
              }
            },
            fields: 'userEnteredFormat(backgroundColor,textFormat)'
          }
        },
        
        // Format Comments sheet header
        {
          repeatCell: {
            range: {
              sheetId: 1,
              startRowIndex: 0,
              endRowIndex: 1
            },
            cell: {
              userEnteredFormat: {
                backgroundColor: { red: 0.2, green: 0.8, blue: 0.4 },
                textFormat: { bold: true, foregroundColor: { red: 1.0, green: 1.0, blue: 1.0 } }
              }
            },
            fields: 'userEnteredFormat(backgroundColor,textFormat)'
          }
        },
        
        // Format Profiles sheet header
        {
          repeatCell: {
            range: {
              sheetId: 2,
              startRowIndex: 0,
              endRowIndex: 1
            },
            cell: {
              userEnteredFormat: {
                backgroundColor: { red: 0.8, green: 0.4, blue: 0.2 },
                textFormat: { bold: true, foregroundColor: { red: 1.0, green: 1.0, blue: 1.0 } }
              }
            },
            fields: 'userEnteredFormat(backgroundColor,textFormat)'
          }
        }
      ];
      
      await this.sheets.spreadsheets.batchUpdate({
        spreadsheetId,
        resource: { requests }
      });
      
    } catch (error) {
      console.warn('Failed to format headers:', error);
    }
  }
}
