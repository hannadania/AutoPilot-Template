'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Icons } from '@/components/ui/icons'
import { InsightCard, type Insight } from '@/components/ai/insights/InsightCard'
import { PatternCluster, type Pattern } from '@/components/ai/insights/PatternCluster'
import { ActionCard, type ActionItem } from '@/components/ai/insights/ActionCard'
import { apiClient } from '@/lib/api-client'

// Tab configuration
interface Tab {
  id: string
  label: string
  icon: React.ElementType
}

const tabs: Tab[] = [
  { id: 'summary', label: 'Summary', icon: Icons.activity },
  { id: 'patterns', label: 'Patterns', icon: Icons.layers },
  { id: 'actions', label: 'Actions', icon: Icons.zap },
]

interface InsightsResponse {
  status: string
  insights: Insight[]
  patterns: Pattern[]
  actions: ActionItem[]
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
}

export default function AIInsightsPage() {
  const [activeTab, setActiveTab] = useState('summary')
  const [insights, setInsights] = useState<Insight[]>([])
  const [patterns, setPatterns] = useState<Pattern[]>([])
  const [actions, setActions] = useState<ActionItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [showSuccess, setShowSuccess] = useState(false) // 🟢 New state for success alert!
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  const fetchInsights = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await apiClient.get<InsightsResponse>('/api/insights/')
      if (response && response.status === 'success') {
        setInsights(response.insights || [])
        setPatterns(response.patterns || [])
        setActions(response.actions || [])
      } else {
        setError('Failed to fetch real-time insights.')
      }
    } catch (err) {
      console.error('Error fetching insights:', err)
      setError('Could not connect to the insights engine.')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchInsights()
  }, [fetchInsights])

  const handleAnalyze = async () => {
    setIsAnalyzing(true)
    setError(null)
    setShowSuccess(false) // Reset success alert
    try {
      const response = await apiClient.post<InsightsResponse>('/api/insights/analyze', {})
      if (response && response.status === 'success') {
        setInsights(response.insights || [])
        setPatterns(response.patterns || [])
        setActions(response.actions || [])
        setShowSuccess(true) // 🟢 Trigger success banner!
        
        // Auto-dismiss the success banner after 4 seconds
        setTimeout(() => {
          setShowSuccess(false)
        }, 4000)
      } else {
        setError('Failed to refresh data analysis.')
      }
    } catch (err) {
      console.error('Error running analysis:', err)
      setError('Could not execute the analysis engine.')
    } finally {
      setIsAnalyzing(false)
    }
  }

  const handleInsightAction = useCallback(async (insight: Insight) => {
    switch (insight.action_type) {
      case 'create_policy':
        router.push('/ai/policies?tab=create-with-ai')
        break
      case 'investigate':
      case 'review_duplicate':
        router.push('/workbench')
        break
      default:
        break
    }
  }, [router])

  const handleDismissInsight = useCallback(async (id: string) => {
    setInsights(prev => prev.filter(i => i.id !== id))
  }, [])

  const handleApplyAction = useCallback(async (action: ActionItem) => {
    switch (action.action_type) {
      case 'create_policy':
        router.push('/ai/policies?tab=create-with-ai')
        break
      case 'investigate':
      case 'review_transaction':
        router.push('/workbench')
        break
      default:
        break
    }
  }, [router])

  const criticalCount = insights.filter(i => i.severity === 'critical').length
  const warningCount = insights.filter(i => i.severity === 'warning').length
  const infoCount = insights.filter(i => i.severity === 'info').length

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-brand-navy">AI Insights</h1>
          <p className="text-muted-foreground">
            AI-powered analysis of your data. Discover patterns, anomalies, and optimization opportunities.
          </p>
        </div>
        <Button onClick={handleAnalyze} disabled={isAnalyzing} variant="gradient">
          {isAnalyzing ? (
            <>
              <Icons.loader className="mr-2 h-4 w-4 animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              <Icons.sparkles className="mr-2 h-4 w-4" />
              Run Analysis
            </>
          )}
        </Button>
      </div>

      {/* 🟢 Beautiful Success Banner */}
      <AnimatePresence>
        {showSuccess && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
          >
            <Card className="border-emerald-200 bg-emerald-50/80 text-emerald-800 shadow-sm">
              <CardContent className="p-4 flex items-center gap-2">
                <Icons.checkCircle className="h-5 w-5 text-emerald-600 animate-bounce" />
                <span className="font-semibold">Analysis complete: Database scanned successfully!</span>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {error && (
        <Card className="border-red-200 bg-red-50 text-red-700">
          <CardContent className="p-4 flex items-center gap-2">
            <Icons.alertCircle className="h-5 w-5" />
            <span>{error}</span>
          </CardContent>
        </Card>
      )}

      {/* Stats Cards */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card className="border-red-100 bg-red-50/50">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="rounded-lg bg-red-100 p-3 text-red-600">
              <Icons.alertCircle className="h-6 w-6" />
            </div>
            <div>
              <div className="text-2xl font-bold text-red-700">{criticalCount}</div>
              <p className="text-sm font-medium text-red-600/80">Critical Anomalies</p>
            </div>
          </CardContent>
        </Card>

        <Card className="border-amber-100 bg-amber-50/50">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="rounded-lg bg-amber-100 p-3 text-amber-600">
              <Icons.alertTriangle className="h-6 w-6" />
            </div>
            <div>
              <div className="text-2xl font-bold text-amber-700">{warningCount}</div>
              <p className="text-sm font-medium text-amber-600/80">Active Warnings</p>
            </div>
          </CardContent>
        </Card>

        <Card className="border-brand-navy/10 bg-brand-navy/5">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="rounded-lg bg-brand-navy/10 p-3 text-brand-navy">
              <Icons.sparkles className="h-6 w-6" />
            </div>
            <div>
              <div className="text-2xl font-bold text-brand-navy">{infoCount + patterns.length}</div>
              <p className="text-sm font-medium text-brand-navy/80">Recommendations</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tab Navigation */}
      <div className="flex border-b border-border/40 gap-2">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id
          const Icon = tab.icon
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'relative flex items-center gap-2 rounded-lg px-4 py-2.5',
                'text-sm font-medium transition-all duration-200',
                isActive ? 'text-white' : 'text-muted-foreground hover:text-foreground hover:bg-white/50'
              )}
            >
              {isActive && (
                <motion.div
                  layoutId="active-insight-tab"
                  className="absolute inset-0 bg-brand-navy rounded-lg -z-10"
                  transition={{ type: 'spring', stiffness: 380, damping: 30 }}
                />
              )}
              <Icon className="h-4 w-4" />
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* Tab Content */}
      {isLoading ? (
        <div className="flex h-[300px] items-center justify-center">
          <Icons.loader className="h-8 w-8 animate-spin text-brand-navy" />
        </div>
      ) : (
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            variants={containerVariants}
            initial="hidden"
            animate="visible"
            className="space-y-4"
          >
            {activeTab === 'summary' && (
              <div className="grid gap-4">
                {insights.length === 0 ? (
                  <Card className="border-dashed p-12 text-center">
                    <CardContent className="flex flex-col items-center justify-center">
                      <Icons.sparkles className="h-10 w-10 text-muted-foreground mb-4" />
                      <h3 className="font-semibold text-lg text-brand-navy">No live insights yet</h3>
                      <p className="text-muted-foreground mb-4">Run an analysis to discover real-time patterns.</p>
                      <Button onClick={handleAnalyze}>Generate Insights</Button>
                    </CardContent>
                  </Card>
                ) : (
                  insights.map((insight) => (
                    <motion.div key={insight.id} variants={itemVariants}>
                      <InsightCard
                        insight={insight}
                        onAction={handleInsightAction}
                        onDismiss={handleDismissInsight}
                      />
                    </motion.div>
                  ))
                )}
              </div>
            )}

            {activeTab === 'patterns' && (
              <div className="grid gap-4">
                <motion.div variants={itemVariants}>
                  <PatternCluster patterns={patterns} />
                </motion.div>
              </div>
            )}

            {activeTab === 'actions' && (
              <div className="grid gap-4">
                {actions.length === 0 ? (
                  <p className="text-muted-foreground text-center py-12">No actions recommended at this time.</p>
                ) : (
                  actions.map((action, idx) => (
                    <motion.div key={idx} variants={itemVariants}>
                      <ActionCard action={action} onApply={handleApplyAction} />
                    </motion.div>
                  ))
                )}
              </div>
            )}
          </motion.div>
        </AnimatePresence>
      )}
    </div>
  )
}
