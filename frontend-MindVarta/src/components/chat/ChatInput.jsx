import { useState, useRef, useEffect } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faPaperPlane, faMicrophone } from '@fortawesome/free-solid-svg-icons'
import { useChat } from '../../context/ChatContext'
import { useVoice } from '../../hooks/useVoice'

const WAVE_BARS = 12

export default function ChatInput({ onSend, isTyping, readOnly }) {
  const [text, setText] = useState('')
  const textareaRef = useRef(null)
  const { language, voiceModeEnabled } = useChat()

  const { recording, transcribing, toggleRecording } = useVoice({
    language,
    onTranscript: (transcript) => {
      setText(transcript)
      // Auto-focus textarea so user can review/edit before sending
      setTimeout(() => textareaRef.current?.focus(), 50)
    },
  })

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current
    if (!ta) return
    ta.style.height = 'auto'
    ta.style.height = Math.min(ta.scrollHeight, 200) + 'px'
  }, [text])

  const handleSend = () => {
    const trimmed = text.trim()
    if (!trimmed || isTyping) return
    onSend(trimmed)
    setText('')
    textareaRef.current?.focus()
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const isBusy = recording || transcribing

  return (
    <div className="input-area">
      {readOnly && (
        <div className="read-only-banner">
          <FontAwesomeIcon icon={faMicrophone} style={{ marginRight: 8 }} />
          Read-Only Mode: You are viewing a past conversation. No new messages can be sent.
        </div>
      )}
      <div className="input-wrapper">
        {isBusy ? (
          <div className="voice-wave-container">
            {Array.from({ length: WAVE_BARS }).map((_, i) => (
              <div
                key={i}
                className="voice-wave-bar"
                style={{
                  height: `${20 + Math.random() * 40}%`,
                  animationDelay: `${i * 0.07}s`,
                  animationDuration: `${0.6 + Math.random() * 0.4}s`,
                }}
              />
            ))}
            <span style={{ fontSize: '0.75rem', color: 'var(--accent-blue-bright)', marginLeft: 8, fontWeight: 500 }}>
              {transcribing ? 'Transcribing...' : 'Listening...'}
            </span>
          </div>
        ) : (
          <textarea
            ref={textareaRef}
            className="chat-input"
            placeholder={readOnly ? "This conversation is in read-only mode" : "Type your message..."}
            value={text}
            onChange={e => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            disabled={readOnly}
            aria-label="Type your message"
          />
        )}

        <div className="input-actions">
          <button
            className={`input-action-btn${recording ? ' recording' : ''}`}
            onClick={toggleRecording}
            disabled={!voiceModeEnabled || transcribing || isTyping || readOnly}
            aria-label={voiceModeEnabled ? (recording ? 'Stop recording' : 'Start voice input') : 'Enable voice mode in settings'}
            style={{ color: recording ? '#ef4444' : undefined }}
          >
            <FontAwesomeIcon icon={faMicrophone} />
          </button>

          <button
            className="send-btn"
            onClick={handleSend}
            disabled={!text.trim() || isTyping || isBusy || readOnly}
            aria-label="Send message"
          >
            <FontAwesomeIcon icon={faPaperPlane} />
          </button>
        </div>
      </div>
    </div>
  )
}
