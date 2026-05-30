import { useEffect } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faTimes, faMoon, faSun } from '@fortawesome/free-solid-svg-icons'
import { useTheme } from '../../context/ThemeContext'
import { useChat } from '../../context/ChatContext'
import { useAuth } from '../../context/AuthContext'
import { useNavigate } from 'react-router-dom'
import '../../styles/settings.css'

export default function SettingsModal({ open, onClose }) {
  const { theme, toggleTheme } = useTheme()
  const { language, setLanguage, voiceModeEnabled, setVoiceModeEnabled, muted, setMuted, clearChat } = useChat()
  const { user, signout } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    if (!open) return
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, onClose])

  const handleSignout = async () => {
    await signout(clearChat)
    onClose()
    navigate('/auth')
  }

  if (!open) return null

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()} role="dialog" aria-modal="true" aria-label="Settings">
        <div className="modal-header">
          <h2 className="modal-title">Settings</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close settings">
            <FontAwesomeIcon icon={faTimes} />
          </button>
        </div>

        <div className="modal-body">
          {/* Account */}
          {user && (
            <section className="settings-section">
              <h3 className="settings-section-title">Account</h3>
              <div className="settings-row">
                <div className="settings-row-info">
                  <span className="settings-row-label">{user.name}</span>
                  <span className="settings-row-desc">{user.email}</span>
                </div>
                <button className="settings-signout-btn" onClick={handleSignout}>
                  Sign Out
                </button>
              </div>
            </section>
          )}

          {/* Appearance */}
          <section className="settings-section">
            <h3 className="settings-section-title">Appearance</h3>
            <div className="settings-row">
              <div className="settings-row-info">
                <span className="settings-row-label">Theme</span>
                <span className="settings-row-desc">Choose between dark and light mode</span>
              </div>
              <div className="theme-toggle-group">
                <button className={`theme-opt${theme === 'dark' ? ' active' : ''}`} onClick={() => theme !== 'dark' && toggleTheme()}>
                  <FontAwesomeIcon icon={faMoon} /> Dark
                </button>
                <button className={`theme-opt${theme === 'light' ? ' active' : ''}`} onClick={() => theme !== 'light' && toggleTheme()}>
                  <FontAwesomeIcon icon={faSun} /> Light
                </button>
              </div>
            </div>
          </section>

          {/* Language */}
          <section className="settings-section">
            <h3 className="settings-section-title">Language</h3>
            <div className="settings-row settings-row--column">
              <div className="settings-row-info">
                <span className="settings-row-label">Response Language</span>
                <span className="settings-row-desc">MindVarta will reply in your chosen language</span>
              </div>
              <div className="lang-toggle-group">
                {[
                  { value: 'english', label: 'English' },
                  { value: 'hindi',   label: 'हिंदी' },
                  { value: 'bengali', label: 'বাংলা' },
                ].map(({ value, label }) => (
                  <button
                    key={value}
                    className={`theme-opt${language === value ? ' active' : ''}`}
                    onClick={() => setLanguage(value)}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
          </section>

          {/* Voice */}
          <section className="settings-section">
            <h3 className="settings-section-title">Voice & Audio</h3>
            <div className="settings-row">
              <div className="settings-row-info">
                <span className="settings-row-label">Voice Mode</span>
                <span className="settings-row-desc">Enable microphone input and spoken responses</span>
              </div>
              <label className="toggle-switch">
                <input type="checkbox" checked={voiceModeEnabled} onChange={() => setVoiceModeEnabled(v => !v)} />
                <span className="toggle-slider" />
              </label>
            </div>
            <div className="settings-row">
              <div className="settings-row-info">
                <span className="settings-row-label">Voice Responses</span>
                <span className="settings-row-desc">Have MindVarta speak replies when Voice Mode is on</span>
              </div>
              <label className="toggle-switch">
                <input type="checkbox" checked={!muted} onChange={() => setMuted(m => !m)} disabled={!voiceModeEnabled} />
                <span className="toggle-slider" />
              </label>
            </div>
          </section>

          {/* About */}
          <section className="settings-section">
            <h3 className="settings-section-title">About</h3>
            <div className="settings-about">
              <p className="settings-about-name">MindVarta</p>
              <p className="settings-about-version">Version 1.0.0</p>
              <p className="settings-about-desc">
                A confidential mental health support platform for students.
                Available 24/7, wherever you are.
              </p>
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}
