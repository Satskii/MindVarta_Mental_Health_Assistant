import React from 'react'
import { useNavigate } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faLock, faClock, faLanguage, faComments, faBook, faMoon, faSun } from '@fortawesome/free-solid-svg-icons'
import { useTheme } from '../../context/ThemeContext'
import '../../styles/landing.css'

const features = [
  {
    icon: faLock,
    title: 'Confidential',
    desc: 'Your conversations stay private and secure.',
  },
  {
    icon: faClock,
    title: '24/7 Support',
    desc: 'Get help anytime, day or night, whenever you need it.',
  },
  {
    icon: faLanguage,
    title: 'Multi-Lingual',
    desc: 'Communicate in your preferred language.',
  },
]

export default function LandingPage() {
  const navigate = useNavigate()
  const { theme, toggleTheme } = useTheme()

  return (
    <div className="landing">
      {/* Ambient background */}
      <div className="landing-bg" aria-hidden>
        <div className="orb orb-1" />
        <div className="orb orb-2" />
        <div className="orb orb-3" />
      </div>

      {/* Navbar */}
      <nav className="navbar">
        <span className="navbar-logo">MindVarta</span>
        <div className="navbar-actions">
          <button
            className="theme-toggle"
            onClick={toggleTheme}
            aria-label="Toggle theme"
            title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            <FontAwesomeIcon icon={theme === 'dark' ? faSun : faMoon} />
          </button>
          <button className="btn-get-started" onClick={() => navigate('/auth')}>
            Get Started
          </button>
        </div>
      </nav>

      {/* Hero */}
      <section className="hero">
        <div className="hero-eyebrow">
          <span className="eyebrow-dot" />
          Always here for you
        </div>

        <h1 className="hero-title">
          Your Mind,Your Language,
          <span className="hero-title-accent">Our Support.</span>
        </h1>

        <p className="hero-subtitle">
          A safe space to talk about your thoughts and feelings.
          Get support when you need it most.
        </p>

        <div className="hero-cta-group">
          <button className="btn-primary" onClick={() => navigate('/auth')}>
            <FontAwesomeIcon icon={faComments} />
            Start Talking Now
          </button>

          <button className="btn-secondary" onClick={() => navigate('/documentation')}>
            <FontAwesomeIcon icon={faBook} />
            View Complete Technical Documentation
          </button>
        </div>
      </section>

      {/* Feature cards */}
      <section className="features">
        <div className="features-grid">
          {features.map((f, i) => (
            <div className="feature-card" key={i}>
              <div className="feature-icon">
                <FontAwesomeIcon icon={f.icon} />
              </div>
              <h3 className="feature-title">{f.title}</h3>
              <p className="feature-desc">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}