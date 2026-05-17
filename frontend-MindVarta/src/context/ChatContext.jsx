import { createContext, useContext, useState, useRef, useEffect } from 'react'
import { useAuth } from './AuthContext'

const ChatContext = createContext()
const API_BASE_URL = import.meta.env.VITE_API_URL

const WELCOME_MESSAGES = {
  english: "Hello! I'm here to provide support for your mental health concerns. How are you feeling today?",
  hindi:   "नमस्ते! मैं आपकी मानसिक स्वास्थ्य संबंधी चिंताओं में सहायता के लिए यहाँ हूँ। आज आप कैसा महसूस कर रहे हैं?",
  bengali: "হ্যালো! আমি আপনার মানসিক স্বাস্থ্য সংক্রান্ত উদ্বেগে সহায়তা করতে এখানে আছি। আজ আপনি কেমন অনুভব করছেন?",
}
const FREE_LIMIT = 10

async function speakText(text, language) {
  try {
    const res = await fetch(`${API_BASE_URL}/speak`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ text, language }),
    })
    if (!res.ok) return
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const audio = new Audio(url)
    audio.onended = () => URL.revokeObjectURL(url)
    audio.play()
  } catch (err) {
    console.error('TTS error:', err)
  }
}

export function ChatProvider({ children }) {
  const { language: authLanguage } = useAuth()
  
  const [conversations, setConversations] = useState([])
  const [activeChatId, setActiveChatId] = useState(null)
  const [currentChatId, setCurrentChatId] = useState(null) // Track the most recent/active chat
  const [messages, setMessages] = useState([{
    id: 1,
    role: 'assistant',
    text: WELCOME_MESSAGES['english'],
    timestamp: new Date(),
  }])
  const [isLoading, setIsLoading] = useState(false)
  const [messagesUsed, setMessagesUsed] = useState(0)
  const [limitReached, setLimitReached] = useState(false)
  const [language, setLanguageState] = useState('english')
  const [voiceModeEnabled, setVoiceModeEnabled] = useState(false)
  const [muted, setMuted] = useState(false)
  const [readOnly, setReadOnly] = useState(false)
  const [isViewingPreviousChat, setIsViewingPreviousChat] = useState(false) // Track if viewing previous chat
  const convIdRef = useRef(null)

  // Update welcome message when language changes
  useEffect(() => {
    if (authLanguage) {
      setLanguageState(authLanguage)
      // Update the welcome message if it's the only message shown
      setMessages(prev => {
        if (prev.length === 1 && prev[0].role === 'assistant') {
          return [{ ...prev[0], text: WELCOME_MESSAGES[authLanguage] || WELCOME_MESSAGES.english }]
        }
        return prev
      })
    }
  }, [authLanguage])

  const clearChat = () => {
    setConversations([])
    setActiveChatId(null)
    setCurrentChatId(null)
    setMessages([{ id: Date.now(), role: 'assistant', text: WELCOME_MESSAGES[language] || WELCOME_MESSAGES.english, timestamp: new Date() }])
    setMessagesUsed(0)
    setLimitReached(false)
    setReadOnly(false)
    setIsViewingPreviousChat(false)
    convIdRef.current = null
  }

  const addMessage = (msg) => {
    setMessages(prev => [...prev, { ...msg, id: Date.now(), timestamp: new Date() }])
  }

  const loadConversations = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/conversations`, { credentials: 'include' })
      if (!res.ok) return
      const data = await res.json()
      setConversations(data.conversations || [])
    } catch (_) {}
  }

  const startNewChat = async (chatLanguage = language) => {
    try {
      const res = await fetch(`${API_BASE_URL}/conversations`, {
        method: 'POST',
        credentials: 'include',
      })
      const data = await res.json()
      convIdRef.current = data.conv_id
      setActiveChatId(data.conv_id)
      setCurrentChatId(data.conv_id) // Set as the current/active chat
      setIsViewingPreviousChat(false) // Not viewing previous chat anymore
      setConversations(prev => [
        { conv_id: data.conv_id, title: data.title, msg_count: 0 },
        ...prev,
      ])
    } catch (_) {
      convIdRef.current = null
    }
    setMessages([{
      id: Date.now(),
      role: 'assistant',
      text: WELCOME_MESSAGES[chatLanguage] || WELCOME_MESSAGES.english,
      timestamp: new Date(),
    }])
    setMessagesUsed(0)
    setLimitReached(false)
    setReadOnly(false)
  }

  const sendMessage = async (userMessage) => {
    if (limitReached) return
    setIsLoading(true)
    addMessage({ role: 'user', text: userMessage })

    try {
      const body = { message: userMessage, language }
      if (convIdRef.current) body.conv_id = convIdRef.current

      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(body),
      })

      const data = await response.json()
      const errorDetail = data.detail || data

      if (response.status === 429 && errorDetail.error === 'free_limit_reached') {
        setLimitReached(true)
        addMessage({
          role: 'assistant',
          text: `You've reached the free limit of ${FREE_LIMIT} messages. Start a new chat to continue.`,
        })
        return
      }

      if (!response.ok) {
        throw new Error(errorDetail.error || errorDetail.detail || 'Failed to get response from server')
      }

      if (data.conv_id) convIdRef.current = data.conv_id
      if (data.messages_used !== undefined) setMessagesUsed(data.messages_used)
      if (data.messages_remaining === 0) setLimitReached(true)

      addMessage({ role: 'assistant', text: data.response })
      if (voiceModeEnabled && !muted) speakText(data.response, language)
    } catch (error) {
      console.error('Error sending message:', error)
      addMessage({ role: 'assistant', text: 'Sorry, I encountered an error. Please try again.' })
    } finally {
      setIsLoading(false)
    }
  }

  const selectConversation = (id) => {
    setActiveChatId(id)
    convIdRef.current = id
    setReadOnly(true)
    setIsViewingPreviousChat(id !== currentChatId) // Set to true if viewing a different chat than current
    
    // Fetch messages for the selected conversation
    fetch(`${API_BASE_URL}/conversations/${id}/messages`, { credentials: 'include' })
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (data?.messages) {
          // Format messages for display
          const formattedMessages = data.messages.map((msg, idx) => ({
            id: idx,
            role: msg.role,
            text: msg.content,
            timestamp: new Date()
          }))
          setMessages(formattedMessages)
        }
      })
      .catch(err => console.error('Error loading conversation messages:', err))
  }

  const returnToCurrentChat = () => {
    if (currentChatId) {
      setActiveChatId(currentChatId)
      convIdRef.current = currentChatId
      setIsViewingPreviousChat(false)
      setReadOnly(false)
      
      // Fetch messages for the current conversation
      fetch(`${API_BASE_URL}/conversations/${currentChatId}/messages`, { credentials: 'include' })
        .then(res => res.ok ? res.json() : null)
        .then(data => {
          if (data?.messages) {
            const formattedMessages = data.messages.map((msg, idx) => ({
              id: idx,
              role: msg.role,
              text: msg.content,
              timestamp: new Date()
            }))
            setMessages(formattedMessages)
          }
        })
        .catch(err => console.error('Error loading current conversation messages:', err))
    }
  }

  const deleteConversation = async (convId) => {
    try {
      const res = await fetch(`${API_BASE_URL}/conversations/${convId}`, {
        method: 'DELETE',
        credentials: 'include',
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err?.detail || err?.error || 'Failed to delete conversation')
      }

      setConversations(prev => prev.filter(c => c.conv_id !== convId))

      const deletedWasActive = activeChatId === convId
      const deletedWasCurrent = currentChatId === convId

      if (deletedWasCurrent) {
        setCurrentChatId(null)
        convIdRef.current = null
        setReadOnly(false)
        setIsViewingPreviousChat(false)
        setMessages([{ id: Date.now(), role: 'assistant', text: WELCOME_MESSAGES[language] || WELCOME_MESSAGES.english, timestamp: new Date() }])
        setMessagesUsed(0)
        setLimitReached(false)
        setActiveChatId(null)
      } else if (deletedWasActive && currentChatId) {
        setActiveChatId(currentChatId)
        convIdRef.current = currentChatId
        setReadOnly(false)
        setIsViewingPreviousChat(false)

        try {
          const msgRes = await fetch(`${API_BASE_URL}/conversations/${currentChatId}/messages`, { credentials: 'include' })
          const data = msgRes.ok ? await msgRes.json() : null
          if (data?.messages) {
            const formattedMessages = data.messages.map((msg, idx) => ({
              id: idx,
              role: msg.role,
              text: msg.content,
              timestamp: new Date(),
            }))
            setMessages(formattedMessages)
          }
        } catch (err) {
          console.error('Error loading current conversation after deletion:', err)
        }
      }
    } catch (error) {
      console.error('Error deleting conversation:', error)
      throw error
    }
  }


  const setLanguage = (newLang) => {
    setLanguageState(newLang)
    // Update welcome message immediately if only the greeting is shown
    setMessages(prev => {
      if (prev.length === 1 && prev[0].role === 'assistant') {
        return [{ ...prev[0], text: WELCOME_MESSAGES[newLang] || WELCOME_MESSAGES.english }]
      }
      return prev
    })
    startNewChat(newLang)
  }

  return (
    <ChatContext.Provider value={{
      conversations,
      activeChatId,
      messages,
      isLoading,
      messagesUsed,
      messagesRemaining: FREE_LIMIT - messagesUsed,
      limitReached,
      language,
      setLanguage,
      voiceModeEnabled,
      setVoiceModeEnabled,
      muted,
      setMuted,
      readOnly,
      isViewingPreviousChat,
      loadConversations,
      startNewChat,
      clearChat,
      addMessage,
      sendMessage,
      selectConversation,
      returnToCurrentChat,
      deleteConversation,
    }}>
      {children}
    </ChatContext.Provider>
  )
}

export function useChat() {
  return useContext(ChatContext)
}
