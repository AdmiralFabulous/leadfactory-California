# 🔍 Facebook Group Scraper

A powerful web application that extracts posts, comments, and profile URLs from Facebook groups using Chrome DevTools MCP and exports data to Google Sheets in real-time.

## ✨ Features

- **Web Interface**: Simple URL input with progress dashboard
- **Real-time Progress**: Live updates showing posts, comments, and profiles scraped
- **Chrome DevTools MCP**: Uses accessibility tree for reliable Facebook scraping
- **Google Sheets Export**: Automatic export to organized spreadsheets
- **WebSocket Updates**: Real-time progress tracking and notifications
- **Profile URL Collection**: Extracts and tracks unique user profile URLs

## 🚀 Quick Start

### Prerequisites

- Node.js 22.12.0+ (required by chrome-devtools-mcp)
- Chrome browser
- Google Service Account (for Sheets export)

### Installation

1. **Clone and install dependencies:**
```bash
cd facebook-scraper
npm run install:all
```

2. **Set up environment:**
```bash
cp env.example .env
# Edit .env with your configuration
```

3. **Configure Google Sheets (optional):**
   - Create a Google Cloud Project
   - Enable Google Sheets API
   - Create a Service Account
   - Download credentials.json to project root
   - OR set GOOGLE_CREDENTIALS environment variable

4. **Start the application:**
```bash
npm run dev
```

The app will be available at:
- Frontend: http://localhost:5173
- Backend: http://localhost:3001

## 📊 Data Output

### Google Sheets Structure

**Posts Sheet:**
- Post ID, Author, Author URL, Content, Timestamp, Reactions, Comment Count, Badge, Scraped At

**Comments Sheet:**
- Post ID, Author, Author URL, Content, Timestamp, Scraped At

**Profiles Sheet:**
- Profile URL, First Seen, Type (Post Author/Comment Author/Both)

### Raw Data Format

```json
{
  "posts": [
    {
      "id": "P1",
      "author": "John Smith",
      "authorUrl": "https://facebook.com/profile/john.smith",
      "content": "Just retired after 30 years...",
      "timestamp": "2h",
      "reactions": 15,
      "commentCount": 3,
      "badge": "Top contributor"
    }
  ],
  "comments": [
    {
      "postId": "P1",
      "author": "Jane Doe",
      "authorUrl": "https://facebook.com/profile/jane.doe",
      "content": "Congratulations!",
      "timestamp": "1h"
    }
  ],
  "profiles": ["https://facebook.com/profile/john.smith", ...],
  "summary": {
    "totalPosts": 15,
    "totalComments": 45,
    "uniqueProfiles": 23,
    "scrapedAt": "2024-01-01T12:00:00Z"
  }
}
```

## 🛠️ Technical Architecture

### Backend (Node.js + Express)
- **MCP Integration**: Chrome DevTools MCP for browser automation
- **WebSocket Server**: Real-time progress updates via Socket.IO
- **Google Sheets API**: Automated data export and formatting
- **Accessibility Parsing**: Extracts data from Facebook's accessibility tree

### Frontend (React + Vite)
- **Real-time UI**: Live progress tracking and status updates
- **Responsive Design**: Modern, mobile-friendly interface
- **WebSocket Client**: Connects to backend for live updates

### Chrome DevTools MCP
- **Browser Control**: Navigate, scroll, and interact with Facebook
- **Accessibility Tree**: Extract structured data from Facebook's DOM
- **Isolated Sessions**: Each scraping session runs in clean browser context

## 🔧 Configuration

### Environment Variables

```bash
# Server
PORT=3001
CLIENT_URL=http://localhost:5173

# Google Sheets
GOOGLE_CREDENTIALS_PATH=./credentials.json
# OR
GOOGLE_CREDENTIALS={"type":"service_account",...}

# MCP Options
MCP_HEADLESS=false
MCP_ISOLATED=true
```

### MCP Server Configuration

The app automatically configures Chrome DevTools MCP with:
- Isolated browser sessions
- Accessibility tree snapshots
- Automated scrolling and navigation

## 📱 Usage

1. **Enter Facebook Group URL**: Paste the full group URL
2. **Choose Export Option**: Toggle Google Sheets export on/off
3. **Start Scraping**: Click "Start Scraping" to begin
4. **Monitor Progress**: Watch real-time counters update
5. **View Results**: See summary and access Google Sheets link

## 🔍 How It Works

1. **Navigation**: MCP navigates to Facebook group
2. **Loading**: Scrolls page to load all visible posts
3. **Extraction**: Takes accessibility tree snapshot
4. **Parsing**: Extracts posts, comments, and profile URLs
5. **Export**: Creates organized Google Sheets (if enabled)
6. **Real-time Updates**: WebSocket sends progress to frontend

## 🚨 Important Notes

### Facebook Login
- You may need to manually log into Facebook when browser opens
- The scraper will wait for you to complete login
- Use your own Facebook account with group access

### Rate Limiting
- Includes delays to avoid overwhelming Facebook servers
- Respects Facebook's terms of service
- Limits scrolling to prevent infinite loops

### Privacy & Ethics
- Only scrapes publicly visible group content
- Respects user privacy and Facebook's terms
- Use responsibly and ethically

## 🛡️ Error Handling

- **Authentication Errors**: Clear messages for Google Sheets setup
- **Network Issues**: Retries and graceful degradation
- **Browser Crashes**: Automatic cleanup and session management
- **Rate Limiting**: Built-in delays and respect for server limits

## 🔧 Development

### Project Structure
```
facebook-scraper/
├── server/                 # Backend Node.js application
│   ├── index.js           # Express server + WebSocket
│   ├── facebook-scraper.js # MCP integration + scraping logic
│   └── google-sheets.js   # Google Sheets API integration
├── client/                # React frontend
│   ├── src/
│   │   ├── App.jsx       # Main application component
│   │   └── App.css       # Styling and responsive design
│   └── package.json
├── package.json           # Root package with dev scripts
└── README.md
```

### Development Scripts
```bash
npm run dev          # Start both frontend and backend
npm run server:dev   # Start backend only
npm run client:dev   # Start frontend only
npm run build        # Build for production
```

## 📄 License

This project is for educational and research purposes. Please ensure compliance with Facebook's Terms of Service and applicable laws when using this tool.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

---

**Built with Chrome DevTools MCP • Powered by Real-time WebSockets**
