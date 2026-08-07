'use client'

import { useState, useEffect, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'

interface BackendInsightsResponse {
  status: string
  kpis: {
    active_pos: number
    value_at_risk: string
    delayed_shipments: number
    sole_sources: number
  }
  insights: {
    single_source_exposure: Array<{ id: number; name: string; country: string; x_tier: string }>
    supplier_delay_patterns: Array<{ supplier_name: string; delay_count: number; delay_reason: string }>
    tier_dependency_cascades: Array<{ id: number; component: string; criticality: string; parent_supplier: string; dependent_supplier: string }>
    demand_anomalies: Array<{ item_number: string; forecast_qty: number; actual_demand: number; channel: string; surge_qty: number }>
    expiring_contracts: Array<{ contract_number: string; contract_name: string; end_date: string; status: string }>
  }
}

export default function AIInsightsPage() {
  const [data, setData] = useState<BackendInsightsResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [debugLog, setDebugLog] = useState<string>('Initializing fetch...')

  const fetchInsights = useCallback(async () => {
    setIsLoading(true)
    const targetUrl = 'http://localhost:8001/api/insights/summary'
    setDebugLog(`🔍 DEBUG: Fetching from ${targetUrl}...`)
    
    try {
      const res = await fetch(targetUrl)
      setDebugLog(prev => prev + `\n📥 Response Status: ${res.status} ${res.statusText}`)
      
      if (res.ok) {
        const payload: BackendInsightsResponse = await res.json()
        setData(payload)
        setDebugLog(prev => prev + `\n✅ SUCCESS: Payload received successfully.`)
      } else {
        const errText = await res.text()
        setDebugLog(prev => prev + `\n❌ ERROR: Server returned ${res.status}. Details: ${errText}`)
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : String(err)
      setDebugLog(prev => prev + `\n🚨 EXCEPTION THROWN: ${errorMessage}`)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchInsights()
  }, [fetchInsights])

  return (
    <div className="space-y-6 p-6 max-w-7xl mx-auto text-slate-900">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">AI Supply Chain Insights</h1>
          <p className="mt-1 text-sm text-slate-500">Live neural audit computed directly from Supabase.</p>
        </div>
        <Button onClick={fetchInsights}>Refresh Analytics</Button>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 sm:grid-cols-4">
        <Card><CardContent className="py-6"><p className="text-2xl font-bold">{data?.kpis.active_pos || 0}</p><p className="text-xs text-muted-foreground">Active POs</p></CardContent></Card>
        <Card><CardContent className="py-6"><p className="text-2xl font-bold text-red-600">{data?.kpis.value_at_risk || 'RM 0.00'}</p><p className="text-xs text-muted-foreground">Value at Risk</p></CardContent></Card>
        <Card><CardContent className="py-6"><p className="text-2xl font-bold">{data?.kpis.delayed_shipments || 0}</p><p className="text-xs text-muted-foreground">Delayed Shipments</p></CardContent></Card>
        <Card><CardContent className="py-6"><p className="text-2xl font-bold">{data?.kpis.sole_sources || 0}</p><p className="text-xs text-muted-foreground">Sole-Source Risks</p></CardContent></Card>
      </div>

      {/* Data Breakdown Cards */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Single Source Exposure</CardTitle>
            <CardDescription>Suppliers with no alternative sourcing.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {isLoading ? (
              <p className="text-sm text-slate-500">Loading...</p>
            ) : data?.insights.single_source_exposure.length === 0 ? (
              <p className="text-sm text-slate-500">No sole-source exposures found.</p>
            ) : (
              data?.insights.single_source_exposure.map((item) => (
                <div key={item.id} className="flex justify-between py-2 border-b text-sm">
                  <span className="font-semibold">{item.name} ({item.country})</span>
                  <span className="text-xs bg-indigo-100 text-indigo-800 px-2 py-0.5 rounded">Tier {item.x_tier}</span>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Supplier Delay Patterns</CardTitle>
            <CardDescription>Recurring delivery bottlenecks.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {isLoading ? (
              <p className="text-sm text-slate-500">Loading...</p>
            ) : data?.insights.supplier_delay_patterns.length === 0 ? (
              <p className="text-sm text-slate-500">No delay patterns recorded.</p>
            ) : (
              data?.insights.supplier_delay_patterns.map((item, index) => (
                <div key={index} className="flex justify-between py-2 border-b text-sm">
                  <div>
                    <p className="font-semibold">{item.supplier_name}</p>
                    <p className="text-xs text-slate-500">Reason: {item.delay_reason || 'Unspecified'}</p>
                  </div>
                  <span className="text-xs bg-red-100 text-red-800 px-2 py-0.5 rounded h-fit">{item.delay_count} delays</span>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>

      {/* Debug Box */}
      <div className="rounded-xl border border-slate-300 bg-slate-950 p-4 text-emerald-400 font-mono text-xs shadow-inner">
        <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-2 text-slate-400 font-bold uppercase tracking-wider">
          <span>🛠️ Live API Connection Debugger</span>
          <span className="text-[10px] text-emerald-500">Target: http://localhost:8001/api/insights/summary</span>
        </div>
        <pre className="whitespace-pre-wrap overflow-x-auto">{debugLog}</pre>
      </div>
    </div>
  )
}