import { useState, useEffect } from 'react'
import Sidebar from '../components/chat/Sidebar'
import ChatHeader from '../components/chat/ChatHeader'
import MessageList from '../components/chat/MessageList'
import ChatInput from '../components/chat/ChatInput'
import CrisisModal from '../components/chat/CrisisModal'
import { useChat } from '../context/ChatContext'
import '../styles/chat.css'

export default function ChatPage() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const { sendMessage, isLoading, muted, setMuted, voiceModeEnabled, loadConversations, readOnly, showCrisisModal, setShowCrisisModal, language } = useChat()

  useEffect(() => {
    loadConversations()
  }, [])

  return (
    <div className="chat-layout">
      <Sidebar collapsed={sidebarCollapsed} />

      <div className="chat-main">
        <ChatHeader
          onToggleSidebar={() => setSidebarCollapsed(c => !c)}
          muted={muted}
          voiceModeEnabled={voiceModeEnabled}
          onToggleMute={() => setMuted(m => !m)}
        />

        <MessageList isTyping={isLoading} />

        <ChatInput onSend={sendMessage} isTyping={isLoading} readOnly={readOnly} />
      </div>

      {/* Crisis Modal */}
      <CrisisModal 
        isOpen={showCrisisModal} 
        onClose={() => setShowCrisisModal(false)}
        language={language}
      />
    </div>
  )
}
