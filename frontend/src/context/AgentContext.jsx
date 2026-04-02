import { createContext, useContext, useState, useEffect } from 'react'
import { getAgents, getAgentConversations } from '../services/api'

const AgentContext = createContext(null)

export function AgentProvider({ children }) {
  const [agents, setAgents] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedAgent, setSelectedAgent] = useState(null)
  const [question, setQuestion] = useState('')
  const [uetr, setUetr] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [showMemory, setShowMemory] = useState(null)
  const [conversationHistory, setConversationHistory] = useState([])
  const [historyLoaded, setHistoryLoaded] = useState(false)

  // Multi-turn conversation state
  const [activeConversationId, setActiveConversationId] = useState(null)
  const [turns, setTurns] = useState([])
  const [conversationFull, setConversationFull] = useState(false)
  const [sizeBytes, setSizeBytes] = useState(0)

  // Load agents and conversation history from MongoDB on mount
  useEffect(() => {
    Promise.all([
      getAgents(),
      getAgentConversations(30),
    ])
      .then(([agentsRes, convsRes]) => {
        setAgents(agentsRes.agents || [])
        setConversationHistory(convsRes.conversations || [])
        setHistoryLoaded(true)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const refreshAgents = () => {
    getAgents()
      .then(res => setAgents(res.agents || []))
      .catch(console.error)
  }

  const addTurn = (responseData) => {
    const turn = {
      turnNumber: responseData.turnNumber,
      question: responseData.question,
      uetr: responseData.uetr,
      result: responseData.result,
      timestamp: new Date().toISOString(),
    }
    setTurns(prev => [...prev, turn])
    setActiveConversationId(responseData.conversationId)
    setSizeBytes(responseData.sizeBytes || 0)
    setConversationFull(responseData.conversationFull || false)
    setResult(responseData)

    // Update conversation in history
    setConversationHistory(prev => {
      const existing = prev.findIndex(c => c.conversationId === responseData.conversationId)
      const convDoc = {
        conversationId: responseData.conversationId,
        turns: [...turns, turn],
        sizeBytes: responseData.sizeBytes,
        lastQuestion: responseData.question,
        updatedAt: new Date().toISOString(),
        createdAt: existing >= 0 ? prev[existing].createdAt : new Date().toISOString(),
      }
      if (existing >= 0) {
        const updated = [...prev]
        updated[existing] = convDoc
        return [convDoc, ...updated.filter((_, i) => i !== existing)]
      }
      return [convDoc, ...prev].slice(0, 50)
    })
  }

  const startNewConversation = () => {
    setActiveConversationId(null)
    setTurns([])
    setConversationFull(false)
    setSizeBytes(0)
    setResult(null)
    setQuestion('')
    setError(null)
  }

  const loadConversation = (conv) => {
    setActiveConversationId(conv.conversationId)
    setTurns(conv.turns || [])
    setSizeBytes(conv.sizeBytes || 0)
    setConversationFull((conv.sizeBytes || 0) >= 10240)
    setQuestion('')
    setUetr(conv.turns?.[0]?.uetr || '')
    // Set result to the last turn's response for the result panel
    const lastTurn = conv.turns?.[conv.turns.length - 1]
    if (lastTurn) {
      setResult({
        conversationId: conv.conversationId,
        question: lastTurn.question,
        uetr: lastTurn.uetr,
        result: lastTurn.result,
        turnNumber: lastTurn.turnNumber,
        sizeBytes: conv.sizeBytes,
      })
    }
    setError(null)
  }

  return (
    <AgentContext.Provider value={{
      agents, loading, refreshAgents,
      selectedAgent, setSelectedAgent,
      question, setQuestion,
      uetr, setUetr,
      result, setResult,
      error, setError,
      showMemory, setShowMemory,
      conversationHistory, historyLoaded,
      // Multi-turn
      activeConversationId, turns, conversationFull, sizeBytes,
      addTurn, startNewConversation, loadConversation,
    }}>
      {children}
    </AgentContext.Provider>
  )
}

export function useAgentContext() {
  const ctx = useContext(AgentContext)
  if (!ctx) throw new Error('useAgentContext must be used within AgentProvider')
  return ctx
}
