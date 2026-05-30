import React, { useState, useRef, useEffect } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faArrowLeft, faBars, faChevronDown, faVolumeMute, faVolumeUp, faMicrophone } from '@fortawesome/free-solid-svg-icons'
import { useChat } from '../../context/ChatContext'
import MindVartaLogo from '../../assets/MindVarta_Logo.png'

const LANGUAGES = [
  { code: 'english', label: 'English', flag: '🇬🇧' },
  { code: 'hindi',   label: 'हिंदी',   flag: '🇮🇳' },
  { code: 'bengali', label: 'বাংলা',   flag: '🇧🇩' },
]

export default function ChatHeader({ onToggleSidebar, muted, voiceModeEnabled, onToggleMute }) {
  const { language, setLanguage, isViewingPreviousChat, returnToCurrentChat } = useChat()
  const [open, setOpen] = useState(false)
  const dropdownRef = useRef(null)

  const activeLang = LANGUAGES.find(l => l.code === language) || LANGUAGES[0]

  useEffect(() => {
    const handler = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  return (
    <header className="chat-header">
      <div className="chat-header-left">
        {/* Back button - show when viewing previous chat */}
        {isViewingPreviousChat && (
          <button 
            className="back-btn" 
            onClick={returnToCurrentChat} 
            aria-label="Back to current chat"
            title="Back to current chat"
          >
            <FontAwesomeIcon icon={faArrowLeft} />
            Back
          </button>
        )}
        
        {/* Sidebar toggle */}
        <button className="sidebar-toggle" onClick={onToggleSidebar} aria-label="Toggle sidebar">
          <FontAwesomeIcon icon={faBars} />
        </button>

        {/* Language selector */}
        <div className="language-selector" ref={dropdownRef} onClick={() => setOpen(o => !o)}>
          <span style={{ fontSize: '1.1rem' }}>{activeLang.flag}</span>
          <span>{activeLang.label}</span>
          <FontAwesomeIcon icon={faChevronDown} style={{ marginLeft: 6, fontSize: '0.75rem' }} />

          {open && (
            <div className="language-dropdown">
              {LANGUAGES.map(l => (
                <div
                  key={l.code}
                  className={`lang-option${activeLang.code === l.code ? ' selected' : ''}`}
                  onClick={(e) => { e.stopPropagation(); setLanguage(l.code); setOpen(false) }}
                >
                  <span style={{ fontSize: '1rem' }}>{l.flag}</span>
                  {l.label}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="chat-header-right">
        {/* Mute toggle */}
        <button
          className="header-icon-btn"
          onClick={onToggleMute}
          aria-label={!voiceModeEnabled ? 'Voice mode is off' : muted ? 'Unmute' : 'Mute'}
          title={!voiceModeEnabled ? 'Enable voice mode in settings' : muted ? 'Unmute responses' : 'Mute responses'}
          disabled={!voiceModeEnabled}
        >
          {!voiceModeEnabled ? (
            <FontAwesomeIcon icon={faMicrophone} />
          ) : muted ? (
            <FontAwesomeIcon icon={faVolumeMute} />
          ) : (
            <FontAwesomeIcon icon={faVolumeUp} />
          )}
        </button>

        {/* Logo */}
        <div className="logo-btn" title="MindVarta">
          <img src={MindVartaLogo} alt="MindVarta Logo" className="logo-image" />
        </div>
      </div>
    </header>
  )
}
