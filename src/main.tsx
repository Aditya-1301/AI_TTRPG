import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import App from './App.tsx'
import { SupabaseProvider } from './contexts/SupabaseContext.tsx'
import { GameProvider } from './contexts/GameContext.tsx'
import { VoiceProvider } from './contexts/VoiceContext.tsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <SupabaseProvider>
        <VoiceProvider>
          <GameProvider>
            <App />
            <Toaster 
              position="top-right"
              toastOptions={{
                duration: 4000,
                style: {
                  background: '#1f2937',
                  color: '#f9fafb',
                  border: '1px solid #374151',
                },
              }}
            />
          </GameProvider>
        </VoiceProvider>
      </SupabaseProvider>
    </BrowserRouter>
  </React.StrictMode>,
)