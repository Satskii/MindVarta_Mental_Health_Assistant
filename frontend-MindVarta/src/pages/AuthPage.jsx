import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faUser, faEnvelope, faLock, faShield, faComments } from '@fortawesome/free-solid-svg-icons'
import { useAuth } from '../context/AuthContext'
import '../styles/auth.css'

function AuthPage() {
  const navigate = useNavigate()
  const { signup, signin } = useAuth()
  const [mode, setMode] = useState('signin')
  const [formData, setFormData] = useState({ name: '', email: '', password: '', confirmPassword: '' })
  const [errors, setErrors] = useState({})
  const [serverError, setServerError] = useState('')
  const [successMsg, setSuccessMsg] = useState('')
  const [loading, setLoading] = useState(false)

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
    setErrors((prev) => ({ ...prev, [name]: '' }))
  }

  const validate = () => {
    const newErrors = {}
    if (mode === 'signup' && !formData.name.trim()) newErrors.name = 'Name is required'
    if (!formData.email.trim()) newErrors.email = 'Email is required'
    else if (!/\S+@\S+\.\S+/.test(formData.email)) newErrors.email = 'Enter a valid email'
    if (!formData.password) newErrors.password = 'Password is required'
    else if (formData.password.length < 6) newErrors.password = 'Password must be at least 6 characters'
    if (mode === 'signup') {
      if (!formData.confirmPassword) newErrors.confirmPassword = 'Please confirm your password'
      else if (formData.password !== formData.confirmPassword) newErrors.confirmPassword = 'Passwords do not match'
    }
    return newErrors
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const validationErrors = validate()
    if (Object.keys(validationErrors).length > 0) { setErrors(validationErrors); return }
    setLoading(true)
    setServerError('')
    try {
      if (mode === 'signup') {
        await signup(formData.name, formData.email, formData.password)
        switchMode('signin')
        setSuccessMsg('Account created! Please sign in.')
        setFormData(prev => ({ ...prev, email: formData.email }))
      } else {
        await signin(formData.email, formData.password)
        navigate('/chat')
      }
    } catch (err) {
      setServerError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const switchMode = (newMode) => {
    setMode(newMode)
    setFormData({ name: '', email: '', password: '', confirmPassword: '' })
    setErrors({})
    setServerError('')
    setSuccessMsg('')
  }

  return (
    <div className="auth-root">
      <div className="auth-blob auth-blob-1" />
      <div className="auth-blob auth-blob-2" />

      <div className="auth-card">
        <div className="auth-logo" onClick={() => navigate('/')}>MindVarta</div>

        <div className="auth-tabs">
          <button type="button" className={`auth-tab ${mode === 'signin' ? 'active' : ''}`} onClick={() => switchMode('signin')}>Sign In</button>
          <button type="button" className={`auth-tab ${mode === 'signup' ? 'active' : ''}`} onClick={() => switchMode('signup')}>Sign Up</button>
          <div className={`auth-tab-indicator ${mode === 'signup' ? 'right' : 'left'}`} />
        </div>

        <div className="auth-heading">
          <h2>{mode === 'signin' ? 'Welcome back' : 'Create your account'}</h2>
          <p>{mode === 'signin' ? 'Sign in to continue your journey' : 'Start your mental wellness journey today'}</p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          {mode === 'signup' && (
            <div className={`auth-field ${errors.name ? 'has-error' : ''}`}>
              <label htmlFor="name">Full Name</label>
              <div className="auth-input-wrap">
                <span className="auth-input-icon">
                  <FontAwesomeIcon icon={faUser} />
                </span>
                <input id="name" name="name" type="text" placeholder="Your full name"
                  value={formData.name} onChange={handleChange} autoComplete="name" />
              </div>
              {errors.name && <span className="auth-error">{errors.name}</span>}
            </div>
          )}

          <div className={`auth-field ${errors.email ? 'has-error' : ''}`}>
            <label htmlFor="email">Email Address</label>
            <div className="auth-input-wrap">
              <span className="auth-input-icon">
                <FontAwesomeIcon icon={faEnvelope} />
              </span>
              <input id="email" name="email" type="email" placeholder="you@example.com"
                value={formData.email} onChange={handleChange} autoComplete="email" />
            </div>
            {errors.email && <span className="auth-error">{errors.email}</span>}
          </div>

          <div className={`auth-field ${errors.password ? 'has-error' : ''}`}>
            <label htmlFor="password">Password</label>
            <div className="auth-input-wrap">
              <span className="auth-input-icon">
                <FontAwesomeIcon icon={faLock} />
              </span>
              <input id="password" name="password" type="password"
                placeholder={mode === 'signup' ? 'Create a password' : 'Enter your password'}
                value={formData.password} onChange={handleChange}
                autoComplete={mode === 'signin' ? 'current-password' : 'new-password'} />
            </div>
            {errors.password && <span className="auth-error">{errors.password}</span>}
          </div>

          {mode === 'signup' && (
            <div className={`auth-field ${errors.confirmPassword ? 'has-error' : ''}`}>
              <label htmlFor="confirmPassword">Confirm Password</label>
              <div className="auth-input-wrap">
                <span className="auth-input-icon">
                  <FontAwesomeIcon icon={faShield} />
                </span>
                <input id="confirmPassword" name="confirmPassword" type="password"
                  placeholder="Re-enter your password" value={formData.confirmPassword}
                  onChange={handleChange} autoComplete="new-password" />
              </div>
              {errors.confirmPassword && <span className="auth-error">{errors.confirmPassword}</span>}
            </div>
          )}

          {mode === 'signin' && (
            <div className="auth-forgot">
              <button type="button" className="auth-switch-link" onClick={() => navigate('/forgot-password')}>
                Forgot password?
              </button>
            </div>
          )}

          {serverError && <div className="auth-server-error">{serverError}</div>}
          {successMsg && <div className="auth-success-msg">{successMsg}</div>}

          <button type="submit" className="auth-submit-btn" disabled={loading}>
            {loading ? <span className="auth-spinner" /> : (
              <>
                <FontAwesomeIcon icon={faComments} />
                {mode === 'signin' ? 'Sign In' : 'Create Account'}
              </>
            )}
          </button>
        </form>

        <p className="auth-switch-text">
          {mode === 'signin' ? "Don't have an account? " : 'Already have an account? '}
          <button type="button" className="auth-switch-link" onClick={() => switchMode(mode === 'signin' ? 'signup' : 'signin')}>
            {mode === 'signin' ? 'Sign Up' : 'Sign In'}
          </button>
        </p>
      </div>
    </div>
  )
}

export default AuthPage
