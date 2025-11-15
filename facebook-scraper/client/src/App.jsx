import { useState, useEffect } from 'react'
import { io } from 'socket.io-client'
import './App.css'

function App() {
  const [url, setUrl] = useState('https://www.facebook.com/groups/epicretire')
  const [isScrapingActive, setIsScrapingActive] = useState(false)
  const [exportToSheets, setExportToSheets] = useState(true)
  const [exportToCSV, setExportToCSV] = useState(true)
  const [currentSession, setCurrentSession] = useState(null)
  const [progress, setProgress] = useState({
    posts: 0,
    comments: 0,
    profiles: 0
  })
  const [status, setStatus] = useState('idle')
  const [message, setMessage] = useState('')
  const [results, setResults] = useState(null)
  const [sheetUrl, setSheetUrl] = useState('')
  const [csvFiles, setCsvFiles] = useState(null)
  const [socket, setSocket] = useState(null)

  useEffect(() => {
    // Initialize WebSocket connection
    const newSocket = io(import.meta.env.VITE_SERVER_URL || 'http://localhost:3001')
    setSocket(newSocket)

    newSocket.on('connect', () => {
      console.log('Connected to server')
    })

    newSocket.on('scraping-progress', (data) => {
      if (data.sessionId === currentSession) {
        setStatus(data.status)
        setMessage(data.message)
        setProgress(data.progress)
      }
    })

    newSocket.on('scraping-complete', (data) => {
      if (data.sessionId === currentSession) {
        setStatus('complete')
        setMessage(data.message)
        setResults(data.data)
        setSheetUrl(data.sheetUrl || '')
        setCsvFiles(data.csvFiles || null)
        setIsScrapingActive(false)
      }
    })

    newSocket.on('scraping-error', (data) => {
      if (data.sessionId === currentSession) {
        setStatus('error')
        setMessage(data.error)
        setIsScrapingActive(false)
      }
    })

    return () => {
      newSocket.close()
    }
  }, [currentSession])

  const handleStartScraping = async () => {
    if (!url.trim()) {
      alert('Please enter a Facebook group URL')
      return
    }

    if (!url.includes('facebook.com/groups/')) {
      alert('Please enter a valid Facebook group URL')
      return
    }

    try {
      setIsScrapingActive(true)
      setStatus('starting')
      setMessage('Initializing scraper...')
      setProgress({ posts: 0, comments: 0, profiles: 0 })
      setResults(null)
      setSheetUrl('')

      const response = await fetch(`${import.meta.env.VITE_SERVER_URL || 'http://localhost:3001'}/api/scrape`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          url: url.trim(),
          exportToSheets,
          exportToCSV
        })
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || 'Failed to start scraping')
      }

      setCurrentSession(data.sessionId)
      setMessage(data.message)

    } catch (error) {
      setStatus('error')
      setMessage(error.message)
      setIsScrapingActive(false)
    }
  }

  const handleReset = () => {
    setUrl('https://www.facebook.com/groups/epicretire')
    setIsScrapingActive(false)
    setCurrentSession(null)
    setProgress({ posts: 0, comments: 0, profiles: 0 })
    setStatus('idle')
    setMessage('')
    setResults(null)
    setSheetUrl('')
    setCsvFiles(null)
  }

  const getStatusColor = () => {
    switch (status) {
      case 'complete': return '#10b981'
      case 'error': return '#ef4444'
      case 'idle': return '#6b7280'
      default: return '#3b82f6'
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>🔍 Epic Retire Group Scraper</h1>
        <p>Extract posts, comments, and profile URLs from the Epic Retire Facebook group</p>
      </header>

      <main className="app-main">
        <div className="scraper-form">
          <div className="form-group">
            <label htmlFor="url">Facebook Group URL:</label>
            <input
              id="url"
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://www.facebook.com/groups/your-group"
              disabled={isScrapingActive}
              className="url-input"
            />
          </div>

          <div className="form-group checkbox-group">
            <label>
              <input
                type="checkbox"
                checked={exportToCSV}
                onChange={(e) => setExportToCSV(e.target.checked)}
                disabled={isScrapingActive}
              />
              Export to CSV files (backup)
            </label>
          </div>

          <div className="form-group checkbox-group">
            <label>
              <input
                type="checkbox"
                checked={exportToSheets}
                onChange={(e) => setExportToSheets(e.target.checked)}
                disabled={isScrapingActive}
              />
              Export to Google Sheets
            </label>
          </div>

          <div className="form-actions">
            <button
              onClick={handleStartScraping}
              disabled={isScrapingActive || !url.trim()}
              className="start-button"
            >
              {isScrapingActive ? 'Scraping...' : 'Start Scraping'}
            </button>
            
            {(results || status === 'error') && (
              <button onClick={handleReset} className="reset-button">
                Reset
              </button>
            )}
          </div>
        </div>

        {(isScrapingActive || results || status === 'error') && (
          <div className="progress-section">
            <div className="status-bar" style={{ backgroundColor: getStatusColor() }}>
              <div className="status-content">
                <span className="status-text">{status.toUpperCase()}</span>
                <span className="status-message">{message}</span>
              </div>
            </div>

            <div className="progress-grid">
              <div className="progress-item">
                <div className="progress-number">{progress.posts}</div>
                <div className="progress-label">Posts Scraped</div>
              </div>
              
              <div className="progress-item">
                <div className="progress-number">{progress.comments}</div>
                <div className="progress-label">Comments Scraped</div>
              </div>
              
              <div className="progress-item">
                <div className="progress-number">{progress.profiles}</div>
                <div className="progress-label">Unique Profiles</div>
              </div>
            </div>

            {isScrapingActive && (
              <div className="loading-animation">
                <div className="spinner"></div>
                <p>Scraping in progress...</p>
              </div>
            )}

            {results && (
              <div className="results-section">
                <h3>✅ Scraping Complete!</h3>
                <div className="results-summary">
                  <p><strong>Total Posts:</strong> {results.summary.totalPosts}</p>
                  <p><strong>Total Comments:</strong> {results.summary.totalComments}</p>
                  <p><strong>Unique Profiles:</strong> {results.summary.uniqueProfiles}</p>
                  <p><strong>Scraped At:</strong> {new Date(results.summary.scrapedAt).toLocaleString()}</p>
                </div>

                {sheetUrl && (
                  <div className="sheets-link">
                    <p><strong>📊 Google Sheets:</strong></p>
                    <a href={sheetUrl} target="_blank" rel="noopener noreferrer" className="sheet-link">
                      Open in Google Sheets
                    </a>
                  </div>
                )}

                {csvFiles && (
                  <div className="csv-files">
                    <p><strong>📁 CSV Files Created:</strong></p>
                    <div className="csv-file-list">
                      <p>✅ Posts: {csvFiles.posts}</p>
                      <p>✅ Comments: {csvFiles.comments}</p>
                      <p>✅ Profiles: {csvFiles.profiles}</p>
                      <p>✅ Summary: {csvFiles.summary}</p>
                    </div>
                    <p className="csv-note">Files saved to: <code>exports/</code> directory</p>
                  </div>
                )}

                <details className="raw-data">
                  <summary>View Raw Data</summary>
                  <pre>{JSON.stringify(results, null, 2)}</pre>
                </details>
              </div>
            )}
          </div>
        )}
      </main>

      <footer className="app-footer">
        <p>Powered by Chrome DevTools MCP • Real-time WebSocket updates</p>
      </footer>
    </div>
  )
}

export default App