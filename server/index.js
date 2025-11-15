import express from 'express';
import { createServer } from 'http';
import { Server } from 'socket.io';
import cors from 'cors';
import dotenv from 'dotenv';
import { MCPFacebookScraper } from './mcp-facebook-scraper.js';
import { GoogleSheetsExporter } from './google-sheets.js';
import { CSVExporter } from './csv-exporter.js';

dotenv.config();

const app = express();
const server = createServer(app);
const io = new Server(server, {
  cors: {
    origin: process.env.CLIENT_URL || "http://localhost:5173",
    methods: ["GET", "POST"]
  }
});

app.use(cors());
app.use(express.json());

// Store active scraping sessions
const activeSessions = new Map();

// API Routes
app.post('/api/scrape', async (req, res) => {
  try {
    const { url, exportToSheets = false, exportToCSV = true } = req.body;
    
    if (!url) {
      return res.status(400).json({ error: 'URL is required' });
    }

    // Validate Facebook group URL - specifically target epicretire group
    if (!url.includes('facebook.com/groups/')) {
      return res.status(400).json({ error: 'Please provide a valid Facebook group URL' });
    }

    // Default to epicretire group if no specific URL provided
    const targetUrl = url.includes('epicretire') ? url : 'https://www.facebook.com/groups/epicretire';

    const sessionId = Date.now().toString();
    const scraper = new MCPFacebookScraper(io, sessionId);
    
    activeSessions.set(sessionId, {
      scraper,
      status: 'starting',
      url: targetUrl,
      exportToSheets,
      exportToCSV
    });

    // Start scraping in background
    scraper.scrape(targetUrl).then(async (data) => {
      const session = activeSessions.get(sessionId);
      let sheetUrl = '';
      let csvFiles = null;
      
      // Always export CSV as backup
      if (session && session.exportToCSV) {
        try {
          const csvExporter = new CSVExporter();
          csvFiles = await csvExporter.exportData(data, 'epicretire-group');
          console.log('✅ CSV backup created successfully');
        } catch (error) {
          console.error('CSV export error:', error);
        }
      }
      
      // Export to Google Sheets if requested
      if (session && session.exportToSheets) {
        try {
          const exporter = new GoogleSheetsExporter();
          sheetUrl = await exporter.exportData(data, `Epic Retire Group - ${new Date().toISOString()}`);
          
          io.emit('scraping-complete', {
            sessionId,
            data,
            sheetUrl,
            csvFiles,
            message: 'Scraping completed! Exported to Google Sheets and CSV files.'
          });
        } catch (error) {
          console.error('Google Sheets export error:', error);
          io.emit('scraping-complete', {
            sessionId,
            data,
            csvFiles,
            error: 'Scraping completed but Google Sheets export failed',
            message: 'Data scraped successfully and exported to CSV files'
          });
        }
      } else {
        io.emit('scraping-complete', {
          sessionId,
          data,
          csvFiles,
          message: 'Scraping completed successfully! CSV files created.'
        });
      }
      
      activeSessions.delete(sessionId);
    }).catch((error) => {
      console.error('Scraping error:', error);
      io.emit('scraping-error', {
        sessionId,
        error: error.message || 'Scraping failed'
      });
      activeSessions.delete(sessionId);
    });

    res.json({ 
      sessionId, 
      message: 'Scraping started for Epic Retire group',
      status: 'started',
      targetUrl
    });

  } catch (error) {
    console.error('API error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

app.get('/api/sessions/:sessionId', (req, res) => {
  const { sessionId } = req.params;
  const session = activeSessions.get(sessionId);
  
  if (!session) {
    return res.status(404).json({ error: 'Session not found' });
  }
  
  res.json({
    sessionId,
    status: session.status,
    url: session.url,
    exportToSheets: session.exportToSheets
  });
});

app.get('/api/sessions', (req, res) => {
  const sessions = Array.from(activeSessions.entries()).map(([id, session]) => ({
    sessionId: id,
    status: session.status,
    url: session.url,
    exportToSheets: session.exportToSheets
  }));
  
  res.json({ sessions });
});

// WebSocket connection handling
io.on('connection', (socket) => {
  console.log('Client connected:', socket.id);
  
  socket.on('disconnect', () => {
    console.log('Client disconnected:', socket.id);
  });
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

const PORT = process.env.PORT || 3001;
server.listen(PORT, () => {
  console.log(`Facebook Scraper Server running on port ${PORT}`);
  console.log(`WebSocket server ready for real-time updates`);
});
