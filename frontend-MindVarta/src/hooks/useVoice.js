import { useState, useRef, useCallback } from 'react'

const API_BASE_URL = import.meta.env.VITE_API_URL

/**
 * useVoice — records audio via MediaRecorder, sends to Whisper STT endpoint,
 * and calls onTranscript(text) with the result.
 */
export function useVoice({ onTranscript, language = 'english' }) {
  const [recording, setRecording] = useState(false)
  const [transcribing, setTranscribing] = useState(false)
  const mediaRecorderRef = useRef(null)
  const streamRef = useRef(null)
  const chunksRef = useRef([])

  const startRecording = useCallback(async () => {
    try {
      console.log('[VOICE] Requesting microphone access...')
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      console.log('[VOICE] ✅ Microphone access granted')
      streamRef.current = stream
      
      const mr = new MediaRecorder(stream)
      mediaRecorderRef.current = mr
      chunksRef.current = []

      mr.ondataavailable = (e) => {
        if (e.data.size > 0) {
          console.log(`[VOICE] Data chunk: ${e.data.size} bytes`)
          chunksRef.current.push(e.data)
        }
      }

      mr.onerror = (e) => {
        console.error('[VOICE] ❌ MediaRecorder error:', e.error)
      }

      mr.onstop = async () => {
        console.log('[VOICE] MediaRecorder onstop callback fired')
        
        // Stop all stream tracks
        if (streamRef.current) {
          streamRef.current.getTracks().forEach(t => {
            console.log(`[VOICE] Stopping stream track: ${t.kind}`)
            t.stop()
          })
          streamRef.current = null
        }
        
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        console.log(`[VOICE] Created blob from ${chunksRef.current.length} chunks, size: ${blob.size} bytes`)
        
        if (blob.size === 0) {
          console.error('[VOICE] ❌ Audio blob is empty! No chunks collected')
          setRecording(false)
          setTranscribing(false)
          return
        }
        
        console.log(`[VOICE] Recording stopped. Audio blob size: ${blob.size} bytes, Language: ${language}`)

        // Send to Whisper STT endpoint
        setTranscribing(true)
        try {
          const formData = new FormData()
          formData.append('audio', blob, 'recording.webm')
          formData.append('language', language)

          console.log('[VOICE] Sending audio to /transcribe endpoint...')
          const res = await fetch(`${API_BASE_URL}/transcribe`, {
            method: 'POST',
            credentials: 'include',
            body: formData,
          })

          console.log(`[VOICE] Response status: ${res.status}`)
          
          const data = await res.json()
          console.log('[VOICE] Response data:', data)
          
          if (res.ok && data.transcript) {
            console.log('[VOICE] ✅ Transcription successful:', data.transcript)
            onTranscript(data.transcript)
          } else {
            const errorMsg = data.detail || data.error || 'Unknown error'
            console.error('[VOICE] ❌ Transcription failed:', res.status, errorMsg)
            console.error('[VOICE] Full response:', data)
          }
        } catch (err) {
          console.error('[VOICE] ❌ Transcription request failed:', err)
          console.error('[VOICE] Error details:', err.message, err.stack)
        } finally {
          setTranscribing(false)
          setRecording(false)
        }
      }

      console.log('[VOICE] Starting MediaRecorder...')
      mr.start()
      console.log('[VOICE] MediaRecorder started')
      setRecording(true)
    } catch (err) {
      console.error('[VOICE] ❌ Microphone access denied:', err.message)
      console.error('[VOICE] Error details:', err)
      setRecording(false)
    }
  }, [language, onTranscript])

  const stopRecording = useCallback(() => {
    console.log('[VOICE] stopRecording called')
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      console.log('[VOICE] Calling mediaRecorder.stop()')
      mediaRecorderRef.current.stop()
      // Don't set recording to false here - let onstop callback handle it
    } else {
      console.warn('[VOICE] ⚠️ MediaRecorder not in recording state')
    }
  }, [])

  const toggleRecording = useCallback(() => {
    console.log('[VOICE] toggleRecording called, recording state:', recording)
    if (recording) {
      console.log('[VOICE] Currently recording, stopping...')
      stopRecording()
    } else {
      console.log('[VOICE] Not recording, starting...')
      startRecording()
    }
  }, [recording, startRecording, stopRecording])

  return { recording, transcribing, toggleRecording }
}
