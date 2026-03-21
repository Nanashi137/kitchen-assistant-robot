import { useState } from 'react'
import './App.css'
import { AuthScreen } from './screens/AuthScreen'
import { ChatScreen } from './screens/ChatScreen'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

function App() {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('auth_token'))
  const [tokenType, setTokenType] = useState<string>(() => localStorage.getItem('auth_token_type') || 'bearer')

  const handleAuthSuccess = (nextToken: string, nextTokenType: string) => {
    setToken(nextToken)
    setTokenType(nextTokenType || 'bearer')
  }

  const handleLogout = () => {
    try {
      localStorage.removeItem('auth_token')
      localStorage.removeItem('auth_token_type')
    } catch {
      
    }
    setToken(null)
  }

  if (!token) {
    return <AuthScreen apiBaseUrl={API_BASE_URL} onAuthSuccess={handleAuthSuccess} />
  }

  return (
    <ChatScreen
      apiBaseUrl={API_BASE_URL}
      token={token}
      tokenType={tokenType}
      onLogout={handleLogout}
    />
  )
}

export default App
