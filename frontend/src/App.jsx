import { useState } from 'react'
import './App.css'

function App() {
  const [file, setFile] = useState(null)
  const [analysisResult, setAnalysisResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [selectedTheme, setSelectedTheme] = useState(null)

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
    }
  }

  const handleUpload = async () => {
    if (!file) return

    setLoading(true)
    setError(null)
    
    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error('Upload failed')
      }

      const data = await response.json()
      setAnalysisResult(data.analysis)
    } catch (err) {
      setError(err.message || 'An error occurred during analysis.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app-container">
      <header>
        <h1>AI-Based Feminist Literary Analyzer</h1>
        <p>Upload a novel (PDF) to map the politics of women's bodies, reproduction, and sexuality.</p>
      </header>

      {!analysisResult && !loading && (
        <section className="upload-section">
          <label className="upload-label">
            Choose PDF Novel
            <input type="file" accept=".pdf" onChange={handleFileChange} />
          </label>
          {file && (
            <div style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem' }}>
              <span>Selected: {file.name}</span>
              <button onClick={handleUpload}>Analyze Text</button>
            </div>
          )}
          {error && <p style={{ color: '#ff6b6b', marginTop: '1rem' }}>{error}</p>}
        </section>
      )}

      {loading && (
        <div className="loading">
          Analyzing document with NLP... This may take a minute.
        </div>
      )}

      {analysisResult && (
        <main className="dashboard">
          <button style={{ alignSelf: 'flex-start' }} onClick={() => setAnalysisResult(null)}>Analyze Another File</button>
          
          <div className="card">
            <h2>Feminist Interpretation</h2>
            <p style={{ fontSize: '1.1rem', lineHeight: '1.6', color: '#f0f0f0' }}>
              {analysisResult.interpretation}
            </p>
          </div>

          <div className="card">
            <h2>Theme Intensity Scores</h2>
            <div className="theme-scores">
              {Object.entries(analysisResult.theme_scores).map(([theme, score]) => (
                <div 
                  key={theme} 
                  className={`theme-score-item ${selectedTheme === theme ? 'active' : ''}`}
                  onClick={() => setSelectedTheme(selectedTheme === theme ? null : theme)}
                >
                  <span className="score">{score}</span>
                  <span className="label">{theme}</span>
                </div>
              ))}
            </div>
          </div>

          {selectedTheme && analysisResult.theme_breakdown[selectedTheme] && (
            <div className="card breakdown-card">
              <h2>Breakdown: <span style={{textTransform: 'capitalize', color: '#ff6b6b'}}>{selectedTheme}</span></h2>
              <p>
                <strong>Keywords found: </strong>
                {Object.entries(analysisResult.theme_breakdown[selectedTheme].keywords).map(([kw, count]) => (
                  <span key={kw} className="keyword-tag">{kw} ({count})</span>
                ))}
              </p>
              
              <h3 style={{marginTop: '1.5rem', marginBottom: '1rem'}}>Evidence Snippets</h3>
              <div className="evidence-list">
                {analysisResult.theme_breakdown[selectedTheme].snippets.map((ev, idx) => (
                  <div key={idx} className="evidence-item">
                    <div className="snippet">"{ev.text}"</div>
                    <div className="meta">
                      <span className="theme-tag">Score: {ev.score}</span>
                      <span className="words-tag">Matched: {ev.matched_words.join(', ')}</span>
                    </div>
                  </div>
                ))}
                {analysisResult.theme_breakdown[selectedTheme].snippets.length === 0 && (
                  <p style={{color: '#a0a0a0'}}>No strong evidence snippets found for this theme in the scanned pages.</p>
                )}
              </div>
            </div>
          )}


        </main>
      )}
    </div>
  )
}

export default App
