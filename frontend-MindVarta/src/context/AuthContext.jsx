import { createContext, useContext, useState, useEffect } from 'react'

const AuthContext = createContext()
const API_BASE_URL = import.meta.env.VITE_API_URL

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)       // null = not loaded yet
  const [authReady, setAuthReady] = useState(false)
  const [language, setLanguage] = useState('english')  // Session language preference

  // On mount — check if cookie session is still valid
  useEffect(() => {
    fetch(`${API_BASE_URL}/auth/me`, { credentials: 'include' })
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data?.user) {
          setUser(data.user)
          // Load session language preference
          if (data.user.language) {
            setLanguage(data.user.language)
          }
        }
      })
      .catch(() => {})
      .finally(() => setAuthReady(true))
  }, [])

  const signup = async (name, email, password) => {
    const res = await fetch(`${API_BASE_URL}/auth/signup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ name, email, password }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || 'Signup failed')
    setUser(data.user)
    setLanguage('english')  // Reset to default language on signup
    return data.user
  }

  const signin = async (email, password) => {
    const res = await fetch(`${API_BASE_URL}/auth/signin`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ email, password }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || 'Sign in failed')
    setUser(data.user)
    setLanguage('english')  // Reset to default language on signin
    return data.user
  }

  const signout = async (onSignout) => {
    await fetch(`${API_BASE_URL}/auth/signout`, {
      method: 'POST',
      credentials: 'include',
    })
    setUser(null)
    setLanguage('english')
    if (onSignout) onSignout()  // clear chat state
  }

  return (
    <AuthContext.Provider value={{ user, authReady, language, signup, signin, signout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
