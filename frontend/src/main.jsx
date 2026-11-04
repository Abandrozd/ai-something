import { StrictMode, useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import './index.css'
import App from './App.jsx'
import Login from './pages/Login.jsx'
import Register from './pages/Register.jsx'
import Profile from './pages/Profile.jsx'
import { apiFetch, clearStoredTokens } from './api.js'
import Admin from './pages/Admin.jsx'

clearStoredTokens()

function PrivateRoute({ children }) {
  const [state, setState] = useState('loading')

  useEffect(() => {
    let live = true
    apiFetch('/users/me')
      .then((res) => {
        if (live) setState(res.ok ? 'in' : 'out')
      })
      .catch(() => {
        if (live) setState('out')
      })
    return () => {
      live = false
    }
  }, [])

  if (state === 'loading') return null
  if (state !== 'in') return <Navigate to="/login" replace />
  return children
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route
          path="/profile"
          element={
            <PrivateRoute>
              <Profile />
            </PrivateRoute>
          }
        />
        <Route
          path="/"
          element={
            <PrivateRoute>
              <App />
            </PrivateRoute>
          }
        />
          <Route
              path="/admin"
              element={
                <PrivateRoute>
                  <Admin />
                </PrivateRoute>
              }
            />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)