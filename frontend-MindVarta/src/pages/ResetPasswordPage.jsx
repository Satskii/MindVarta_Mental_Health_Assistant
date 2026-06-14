import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faLock, faShield } from '@fortawesome/free-solid-svg-icons'
import '../styles/auth.css'

const API_BASE_URL = 'http://localhost:10000'

export default function ResetPasswordPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') || ''

  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [loading, setLoading] = useState(false)
  const [serverError, setServerError] = useState('')
  const [successMsg, setSuccessMsg] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setServerError('')
    if (password.length < 6) return setServerError('Password must be at least 6 characters')
    if (password !== confirm) return setServerError('Passwords do not match')
    if (!token) return setServerError('Invalid or missing reset token')

    setLoading(true)
    try {
      const res = await fetch(`${API_BASE_URL}/auth/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, new_password: password }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Reset failed')
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
          <h2>Set new password</h2>
          <p>Choose a strong password for your account</p>
        </div>

        {!successMsg ? (
          <form className="auth-form" onSubmit={handleSubmit} noValidate>
            <div className="auth-field">
              <label htmlFor="password">New Password</label>
              <div className="auth-input-wrap">
                <span className="auth-input-icon">
                  <FontAwesomeIcon icon={faLock} />
                </span>
                <input
                  id="password"
                  type="password"
                  placeholder="At least 6 characters"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  autoComplete="new-password"
                />
              </div>
            </div>

            <div className="auth-field">
              <label htmlFor="confirm">Confirm Password</label>
              <div className="auth-input-wrap">
                <span className="auth-input-icon">
                  <FontAwesomeIcon icon={faShield} />
                </span>
                <input
                  id="confirm"
                  type="password"
                  placeholder="Re-enter your password"
                  value={confirm}
                  onChange={e => setConfirm(e.target.value)}
                  autoComplete="new-password"
                />
              </div>
            </div>

            {serverError && <div className="auth-server-error">{serverError}</div>}

            <button type="submit" className="auth-submit-btn" disabled={loading || !password || !confirm}>
              {loading ? <span className="auth-spinner" /> : 'Reset Password'}
            </button>
          </form>
        ) : (
          <>
            <div className="auth-success-msg" style={{ marginTop: '1rem' }}>{successMsg}</div>
            <button
              className="auth-submit-btn"
              style={{ marginTop: '1rem' }}
              onClick={() => navigate('/auth')}
            >
              Go to Sign In
            </button>
          </>
        )}
      </div>
    </div>
  )
}
