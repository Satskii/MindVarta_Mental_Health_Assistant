import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faComments, faHome, faTrash, faGear, faPlus, faMoon, faSun } from '@fortawesome/free-solid-svg-icons'
import { useTheme } from '../../context/ThemeContext'
import { useChat } from '../../context/ChatContext'
import SettingsModal from './SettingsModal'

// Helper function to format date properly from ISO string
const formatDate = (isoString) => {
  if (!isoString) return ''
  try {
    const date = new Date(isoString)
    // Use UTC getters to ensure we get the correct date regardless of timezone
    const year = date.getUTCFullYear()
    const month = date.getUTCMonth()
    const day = date.getUTCDate()
    const localDate = new Date(year, month, day)
    return localDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  } catch {
    return ''
  }
}

export default function Sidebar({ collapsed }) {
  const navigate = useNavigate()
  const { theme, toggleTheme } = useTheme()
  const { conversations, activeChatId, startNewChat, selectConversation, deleteConversation } = useChat()
  const [settingsOpen, setSettingsOpen] = useState(false)

  const handleDeleteConversation = async (e, convId) => {
    e.stopPropagation()
    const confirmed = window.confirm('Delete this conversation permanently? This cannot be undone.')
    if (!confirmed) return

    try {
      await deleteConversation(convId)
    } catch (error) {
      window.alert(error.message || 'Failed to delete conversation.')
    }
  }

  return (
    <aside className={`sidebar${collapsed ? ' collapsed' : ''}`}>
      {/* Settings Modal */}
      <SettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} />
      {/* Header */}
      <div className="sidebar-header">
        <span className="sidebar-logo">MindVarta</span>
        <button
          className="sidebar-theme-btn"
          onClick={toggleTheme}
          aria-label="Toggle theme"
        >
          <FontAwesomeIcon icon={theme === 'dark' ? faSun : faMoon} />
        </button>
      </div>

      {/* New Chat */}
      <button className="new-chat-btn" onClick={startNewChat}>
        <FontAwesomeIcon icon={faPlus} />
        New Chat
      </button>

      {/* Conversations */}
      <div className="conversations-section">
        <p className="conversations-label">Recent Conversations</p>
        {conversations.map(conv => (
          <div
            key={conv.conv_id}
            className={`conversation-item${activeChatId === conv.conv_id ? ' active' : ''}`}
            onClick={() => selectConversation(conv.conv_id)}
          >
            <span className="conversation-icon">
              <FontAwesomeIcon icon={faComments} />
            </span>
            <div className="conversation-info">
              <div className="conversation-title">{conv.title}</div>
              <div className="conversation-time">
                {formatDate(conv.updated_at)}
              </div>
            </div>
            <button
              className="conversation-delete-btn"
              onClick={(e) => handleDeleteConversation(e, conv.conv_id)}
              aria-label={`Delete ${conv.title}`}
              title="Delete conversation"
            >
              <FontAwesomeIcon icon={faTrash} />
            </button>
          </div>
        ))}
      </div>

      {/* Footer nav */}
      <div className="sidebar-footer">
        <button className="sidebar-nav-btn" onClick={() => navigate('/')}>
          <FontAwesomeIcon icon={faHome} /> Home
        </button>
        <button className="sidebar-nav-btn" onClick={() => setSettingsOpen(true)}>
          <FontAwesomeIcon icon={faGear} /> Settings
        </button>
      </div>
    </aside>
  )
}
