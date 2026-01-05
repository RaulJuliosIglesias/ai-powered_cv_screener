import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'
import { LanguageProvider } from './contexts/LanguageContext'
import { BackgroundTaskProvider } from './contexts/BackgroundTaskContext'
import { PipelineProvider } from './contexts/PipelineContext'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <LanguageProvider>
      <BackgroundTaskProvider>
        <PipelineProvider>
          <App />
        </PipelineProvider>
      </BackgroundTaskProvider>
    </LanguageProvider>
  </React.StrictMode>,
)
