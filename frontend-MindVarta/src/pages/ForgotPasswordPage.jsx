import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faEnvelope } from '@fortawesome/free-solid-svg-icons'
import '../styles/auth.css'

const API_BASE_URL = import.meta.env.VITE_API_URL

export default function ForgotPasswordPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [serverError, setServerError] = useState('')
  const [successMsg, setSuccessMsg] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!email.trim()) return
    setLoading(true)
    setServerError('')
    try {
      const res = await fetch(`${API_BASE_URL}/auth/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim().toLowerCase() }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Something went wrong')
      setSuccessMsg(data.message)
    } catch (err) {
      setServerError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-root">
      <div className="auth-blob auth-blob-1" />
      <div className="auth-blob auth-blob-2" />

      <div className="auth-card">
        <div className="auth-logo" onClick={() => navigate('/')}>MindVarta</div>

        <div className="auth-heading">
          <h2>Forgot password?</h2>
          <p>Enter your email and we'll send you a reset link</p>
        </div>

        {!successMsg ? (
          <form className="auth-form" onSubmit={handleSubmit} noValidate>
            <div className="auth-field">
              <label htmlFor="email">Email Address</label>
              <div className="auth-input-wrap">
                <span className="auth-input-icon">
                  <FontAwesomeIcon icon={faEnvelope} />
                </span>
                <input
                  id="email"
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  autoComplete="email"
                />
              </div>
            </div>

            {serverError && <div className="auth-server-error">{serverError}</div>}

            <button type="submit" className="auth-submit-btn" disabled={loading || !email.trim()}>
              {loading ? <span className="auth-spinner" /> : 'Send Reset Link'}
            </button>
          </form>
        ) : (
          <div className="auth-success-msg" style={{ marginTop: '1rem', textAlign: 'left', lineHeight: 1.6 }}>
            {successMsg}
          </div>
        )}

        <p className="auth-switch-text" style={{ marginTop: '1.25rem' }}>
          <button className="auth-switch-link" onClick={() => navigate('/auth')}>
            ← Back to Sign In
          </button>
        </p>
      </div>
    </div>
  )
}
