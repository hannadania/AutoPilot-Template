'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Icons } from '@/components/ui/icons'
import { apiClient } from '@/lib/api-client'

interface Integration {
  id: string
  name: string
  category: string
  description: string
  status: 'healthy' | 'error'
  latency: string
  last_ping: string
  env_keys: string[]
}

interface DataManagerResponse {
  status: string
  integrations: Integration[]
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.1 } },
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
}

export default function DataManagerPage() {
  const [integrations, setIntegrations] = useState<Integration[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isTesting, setIsTesting] = useState(false)
  const [error, setError] = useState<string | null>(null)

 const fetchStatus = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      console.log('📡 [DATA MANAGER DEBUG] Firing request to: /api/data-manager/status/')
      
      const response = await apiClient.get<DataManagerResponse>('/api/data-manager/status/')
      
      console.log('✅ [DATA MANAGER DEBUG] Connection successful! Response:', response)
      
      if (response && response.status === 'success') {
        setIntegrations(response.integrations || [])
      } else {
        setError('Failed to fetch real-time integration status.')
      }
    } catch (err) {
      console.error('❌ [DATA MANAGER DEBUG] API Connection Failed:', err)
      setError('Could not connect to the integrations registry.')
    } finally {
      setIsLoading(false)
    }
  }, [])


  useEffect(() => {
    fetchStatus()
  }, [fetchStatus])

  const handleTestAll = async () => {
    setIsTesting(true)
    try {
      await fetchStatus()
    } finally {
      setIsTesting(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-brand-navy">Data Manager</h1>
          <p className="text-muted-foreground">
            Registry of connected enterprise systems, channel environments, and active database credentials.
          </p>
        </div>
        <Button onClick={handleTestAll} disabled={isTesting || isLoading} variant="outline" className="border-brand-navy/20 hover:bg-brand-navy/5 text-brand-navy">
          {isTesting ? (
            <>
              <Icons.loader className="mr-2 h-4 w-4 animate-spin" />
              Pinging...
            </>
          ) : (
            <>
              <Icons.activity className="mr-2 h-4 w-4" />
              Test All Connections
            </>
          )}
        </Button>
      </div>

      {error && (
        <Card className="border-red-200 bg-red-50 text-red-700">
          <CardContent className="p-4 flex items-center gap-2">
            <Icons.alertCircle className="h-5 w-5" />
            <span>{error}</span>
          </CardContent>
        </Card>
      )}

      {isLoading ? (
        <div className="flex h-[300px] items-center justify-center">
          <Icons.loader className="h-8 w-8 animate-spin text-brand-navy" />
        </div>
      ) : (
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="grid gap-6 md:grid-cols-2"
        >
          {integrations.map((item) => {
            const isHealthy = item.status === 'healthy'
            return (
              <motion.div key={item.id} variants={itemVariants}>
                <Card className="overflow-hidden border-border/60 hover:shadow-lg transition-all duration-200 bg-white">
                  <div className={cn("h-1 w-full", isHealthy ? "bg-emerald-500" : "bg-red-500")} />
                  <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
                    <div>
                      <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">
                        {item.category}
                      </div>
                      <CardTitle className="text-lg font-bold text-brand-navy">{item.name}</CardTitle>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={cn(
                        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wider",
                        isHealthy ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700"
                      )}>
                        <span className={cn("h-2 w-2 rounded-full", isHealthy ? "bg-emerald-500 animate-pulse" : "bg-emerald-500")} />
                        {item.status}
                      </span>
                    </div>
                  </CardHeader>

                  <CardContent className="space-y-4">
                    <p className="text-sm text-muted-foreground min-h-[48px] leading-relaxed">
                      {item.description}
                    </p>

                    <div className="border-t border-border/40 pt-4 flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">Response Latency</span>
                      <span className="font-semibold text-brand-navy">{item.latency}</span>
                    </div>

                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">Connected Keys</span>
                      <div className="flex flex-wrap gap-1">
                        {item.env_keys.map((key) => (
                          <code key={key} className="text-xs bg-gray-100 text-gray-700 px-1.5 py-0.5 rounded border border-gray-200">
                            {key}
                          </code>
                        ))}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            )
          })}
        </motion.div>
      )}
    </div>
  )
}