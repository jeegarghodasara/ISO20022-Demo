import { createContext, useContext, useState, useEffect } from 'react'
import { getAgents } from '../services/api'

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

  // Load agents once on mount
  useEffect(() => {
    getAgents()
      .then(res => setAgents(res.agents || []))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const refreshAgents = () => {
    getAgents()
      .then(res => setAgents(res.agents || []))
      .catch(console.error)
  }

  const addConversation = (conv) => {
    setConversationHistory(prev => [conv, ...prev].slice(0, 50))
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
      conversationHistory, addConversation,
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
