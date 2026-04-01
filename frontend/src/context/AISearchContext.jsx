import { createContext, useContext, useState, useEffect } from 'react'
import { getAISearchStatus } from '../services/api'

const AISearchContext = createContext(null)

export function AISearchProvider({ children }) {
  const [activeTab, setActiveTab] = useState('natural')
  const [status, setStatus] = useState(null)
  const [query, setQuery] = useState('')
  const [uetrInput, setUetrInput] = useState('')
  const [results, setResults] = useState(null)
  const [error, setError] = useState(null)

  // Load status once
  useEffect(() => {
    getAISearchStatus().then(setStatus).catch(console.error)
  }, [])

  return (
    <AISearchContext.Provider value={{
      activeTab, setActiveTab,
      status,
      query, setQuery,
      uetrInput, setUetrInput,
      results, setResults,
      error, setError,
    }}>
      {children}
    </AISearchContext.Provider>
  )
}

export function useAISearchContext() {
  const ctx = useContext(AISearchContext)
  if (!ctx) throw new Error('useAISearchContext must be used within AISearchProvider')
  return ctx
}
