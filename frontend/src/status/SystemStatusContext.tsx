import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { useAuth } from '../auth/AuthContext'

const SystemStatusContext = createContext<number | null>(null)

export function SystemStatusProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const [activeJobs, setActiveJobs] = useState<number | null>(null)

  useEffect(() => {
    if (!user) {
      setActiveJobs(null)
      return
    }
    const source = new EventSource('/system/status/stream')
    source.onmessage = (event) => setActiveJobs(Number(event.data))
    return () => source.close()
  }, [user])

  return <SystemStatusContext.Provider value={activeJobs}>{children}</SystemStatusContext.Provider>
}

export function useSystemStatus(): number | null {
  return useContext(SystemStatusContext)
}
