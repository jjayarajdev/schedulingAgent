import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { AuthProvider } from './context/AuthContext'
import { PhoneProvider } from './context/PhoneContext'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <PhoneProvider>
          <App />
        </PhoneProvider>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>,
)
