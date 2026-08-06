/* eslint-disable @typescript-eslint/no-explicit-any */
'use client'

import { useState, useEffect, useCallback } from 'react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { CardWatermark } from '@/components/ui/card-watermark'
import { Icons } from '@/components/ui/icons'
import { PolicyCard, type Policy } from '@/components/ai/policies/PolicyCard'
import { PolicyDetailModal } from '@/components/ai/policies/PolicyDetailModal'
import { PolicyEditModal } from '@/components/ai/policies/PolicyEditModal'
import { CreateWithAI } from '@/components/ai/policies/CreateWithAI'
import { PermissionMatrixTab } from '@/components/ai/policies/PermissionMatrixTab'
import { StructuredBuilder } from '@/components/ai/policies/StructuredBuilder'

// ============================================================================
// Types
// ============================================================================

type TabType = 'policies' | 'create-ai' | 'structured' | 'matrix'
type FilterType = 'all' | 'active' | 'inactive' | 'logical' | 'natural_language'
type SortType = 'newest' | 'oldest' | 'priority' | 'name' | 'executions'

// ============================================================================
// Tab Configuration
// ============================================================================

const TABS = [
  { id: 'policies' as TabType, label: 'Policies', Icon: Icons.layers },
  { id: 'create-ai' as TabType, label: 'Create with AI', Icon: Icons.sparkles },
  { id: 'structured' as TabType, label: 'Structured Builder', Icon: Icons.grid },
  { id: 'matrix' as TabType, label: 'Permission Matrix', Icon: Icons.table },
]

// ============================================================================
// Page Component
// ============================================================================

export default function AIPoliciesPage() {
  // State
  const [policies, setPolicies] = useState<Policy[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<TabType>('policies')
  
  // Modal state
  const [selectedPolicy, setSelectedPolicy] = useState<Policy | null>(null)
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false)
  const [editingPolicy, setEditingPolicy] = useState<Policy | null>(null)
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  
  // Filters
  const [filter, setFilter] = useState<FilterType>('all')
  const [sortBy, setSortBy] = useState<SortType>('newest')
  const [searchQuery, setSearchQuery] = useState('')

  // Structured builder state
  const [structuredDSL, setStructuredDSL] = useState<{conditions: Array<{field: string; operator: string; value: string}>; actions: Array<{type: string; value?: string}>; match_mode: 'all' | 'any'} | null>(null)
  const [structuredName, setStructuredName] = useState('')
  const [isSavingStructured, setIsSavingStructured] = useState(false)

  // ============================================================================
  // Data Fetching
  // ============================================================================

  const loadPolicies = useCallback(async () => {
    try {
      setIsLoading(true);
      const timestamp = new Date().getTime();
      const res = await fetch(`http://localhost:8001/api/policies?t=${timestamp}`, {
        cache: 'no-store',
        headers: {
          'Pragma': 'no-cache',
          'Cache-Control': 'no-cache'
        }
      });
      
      const data = await res.json();
      setPolicies(data.policies || []);
    } catch (error) {
      console.error("Failed to load policies", error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeTab === 'policies') {
      loadPolicies()
    }
  }, [activeTab, loadPolicies])

  // ============================================================================
  // Policy Actions
  // ============================================================================

  const handleCardClick = useCallback((policy: Policy) => {
    setSelectedPolicy(policy)
    setIsDetailModalOpen(true)
  }, [])

  const handleEditFromDetail = useCallback((policy: Policy) => {
    setEditingPolicy(policy)
    setIsEditModalOpen(true)
  }, [])

  const togglePolicyStatus = useCallback(async (id: string, currentStatus: boolean, currentValue: any) => {
    const newStatus = !currentStatus;
    setPolicies(prev => prev.map(p => p.id === id ? { ...p, is_active: newStatus } : p))

    try {
      await fetch(`http://localhost:8001/api/policies/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          is_active: newStatus,
          value: currentValue
        }),
      })
    } catch (error) {
      console.error('Failed to update policy in backend:', error)
    }
  }, [])

  const handlePolicyCreate = async (policyData: {
    name: string
    description: string
    naturalLanguage: string
    policyType: 'logical' | 'natural_language'
    dsl: unknown
    refinedInstruction: string | null
    entityName: string | null
    tags: string[]
    priority: number
  }) => {
    try {
      const res = await fetch('http://localhost:8001/api/policies', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: policyData.name,
          description: policyData.description,
          natural_language: policyData.naturalLanguage,
          policy_type: policyData.policyType,
          dsl: policyData.dsl,
          refined_instruction: policyData.refinedInstruction,
          entity_name: policyData.entityName,
          tags: policyData.tags,
          priority: policyData.priority,
          is_active: true
        }),
      })

      if (res.ok) {
        setActiveTab('policies');
        await loadPolicies();
      } else {
        console.error('Failed to save policy to backend');
      }
    } catch (error) {
      console.error('Error saving policy:', error)
    }
  }

  const deletePolicy = async (id: string) => {
    try {
      const res = await fetch(`http://localhost:8001/api/policies/${id}`, {
        method: 'DELETE',
      })
      if (res.ok) {
        await loadPolicies()
      } else {
        console.error('Failed to delete policy')
      }
    } catch (error) {
      console.error('Error deleting policy:', error)
    }
  }

  // ============================================================================
  // Filtering & Sorting
  // ============================================================================

  const filteredPolicies = policies
    .filter((policy) => {
      if (filter === 'active' && !policy.is_active) return false
      if (filter === 'inactive' && policy.is_active) return false
      if (filter === 'logical' && policy.policy_type !== 'logical') return false
      if (filter === 'natural_language' && policy.policy_type !== 'natural_language') return false

      if (searchQuery) {
        const query = searchQuery.toLowerCase()
        return (
          policy.name.toLowerCase().includes(query) ||
          policy.description.toLowerCase().includes(query) ||
          policy.natural_language.toLowerCase().includes(query) ||
          policy.tags.some((tag) => tag.toLowerCase().includes(query))
        )
      }

      return true
    })
    .sort((a, b) => {
      switch (sortBy) {
        case 'newest':
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        case 'oldest':
          return new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
        case 'priority':
          return a.priority - b.priority
        case 'name':
          return a.name.localeCompare(b.name)
        case 'executions':
          return b.execution_count - a.execution_count
        default:
          return 0
      }
    })

  // ============================================================================
  // Stats
  // ============================================================================

  const stats = {
    total: policies.length,
    active: policies.filter((p) => p.is_active).length,
    structured: policies.filter((p) => p.policy_type === 'logical').length,
    natural: policies.filter((p) => p.policy_type === 'natural_language').length,
  }

  // ============================================================================
  // Render
  // ============================================================================

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-display-3 font-bold tracking-tight text-brand-navy lg:text-display-2">
            AI Policies
          </h1>
          <p className="mt-1 text-lg text-muted-foreground">
            Define business rules in natural language. The AI determines the best format.
          </p>
        </div>
        <Button
          variant="gradient"
          onClick={() => setActiveTab('create-ai')}
          className={activeTab !== 'policies' ? 'opacity-50' : ''}
        >
          <Icons.plus className="mr-2 h-4 w-4" />
          Create Policy
        </Button>
      </div>

      {/* Tabs */}
      <div>
        <div className="flex gap-1 p-1.5 bg-gray-100 rounded-xl">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => {
                setActiveTab(tab.id);
                if (tab.id === 'policies') {
                  loadPolicies();
                }
              }}
              className={cn(
                'relative flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors',
                activeTab === tab.id
                  ? 'text-brand-navy bg-white shadow-sm font-semibold'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              <span className="relative z-10 flex items-center gap-2">
                <tab.Icon className="h-4 w-4" />
                {tab.label}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      <div className="mt-6">
        
        {/* POLICIES TAB */}
        {activeTab === 'policies' && (
          <div key="policies-tab" className="space-y-6">
            {/* Stats Bar */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              {[
                { value: stats.total, label: 'Total Policies', icon: Icons.layers, bg: 'bg-brand-navy/10', color: 'text-brand-navy' },
                { value: stats.active, label: 'Active', icon: Icons.check, bg: 'bg-emerald-100', color: 'text-emerald-600' },
                { value: stats.structured, label: 'Structured', icon: Icons.grid, bg: 'bg-blue-100', color: 'text-blue-600' },
                { value: stats.natural, label: 'Natural Language', icon: Icons.brain, bg: 'bg-purple-100', color: 'text-purple-600' },
              ].map((stat) => (
                <div 
                  key={stat.label}
                  className="bg-white rounded-xl border border-gray-200 p-4"
                >
                  <div className="flex items-center gap-3">
                    <div className={cn('p-2 rounded-lg', stat.bg)}>
                      <stat.icon className={cn('h-5 w-5', stat.color)} />
                    </div>
                    <div>
                      <p className={cn('text-2xl font-bold', stat.color)}>
                        {stat.value}
                      </p>
                      <p className="text-xs text-muted-foreground">{stat.label}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Filters & Search */}
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="relative flex-1">
                <Icons.search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search policies..."
                  className={cn(
                    'w-full pl-10 pr-4 py-2.5 rounded-lg border border-input bg-white',
                    'text-sm focus:outline-none focus:ring-2 focus:ring-brand-cornflower/50'
                  )}
                />
              </div>

              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground whitespace-nowrap">Filter:</span>
                <select
                  value={filter}
                  onChange={(e) => setFilter(e.target.value as FilterType)}
                  className="px-3 py-2.5 rounded-lg border border-input bg-white text-sm focus:outline-none focus:ring-2 focus:ring-brand-cornflower/50"
                >
                  <option value="all">All</option>
                  <option value="active">Active</option>
                  <option value="inactive">Inactive</option>
                  <option value="logical">Structured</option>
                  <option value="natural_language">Natural Language</option>
                </select>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground whitespace-nowrap">Sort:</span>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as SortType)}
                  className="px-3 py-2.5 rounded-lg border border-input bg-white text-sm focus:outline-none focus:ring-2 focus:ring-brand-cornflower/50"
                >
                  <option value="newest">Newest</option>
                  <option value="oldest">Oldest</option>
                  <option value="priority">Priority</option>
                  <option value="name">Name</option>
                  <option value="executions">Most Used</option>
                </select>
              </div>
            </div>

            {/* Policy Grid */}
            <div>
              {isLoading ? (
                <div className="flex items-center justify-center py-16">
                  <Icons.loader className="h-8 w-8 animate-spin text-brand-cornflower" />
                </div>
              ) : filteredPolicies.length === 0 ? (
                <Card className="relative overflow-hidden">
                  <CardWatermark opacity={3} scale={1} />
                  <CardContent className="relative z-10 flex flex-col items-center justify-center py-16 text-center">
                    <div className={cn(
                      'mb-4 flex h-16 w-16 items-center justify-center rounded-2xl',
                      'bg-gradient-to-br from-brand-cornflower/20 to-brand-purple/20'
                    )}>
                      <Icons.brain className="h-8 w-8 text-brand-cornflower" strokeWidth={1.5} />
                    </div>
                    <h3 className="font-display text-lg font-semibold text-brand-navy">
                      {searchQuery || filter !== 'all' ? 'No matching policies' : 'No policies yet'}
                    </h3>
                    <p className="mt-1 max-w-sm text-sm text-muted-foreground">
                      {searchQuery || filter !== 'all'
                        ? 'Try adjusting your search or filter criteria.'
                        : 'Create your first AI policy using natural language.'}
                    </p>
                    <Button
                      variant="gradient"
                      className="mt-6"
                      onClick={() => setActiveTab('create-ai')}
                    >
                      <Icons.sparkles className="mr-2 h-4 w-4" />
                      Create with AI
                    </Button>
                  </CardContent>
                </Card>
              ) : (
                <div key={policies.length} className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {filteredPolicies.map((policy) => (
                    <PolicyCard
                      key={policy.id || Math.random()}
                      policy={policy}
                      onClick={handleCardClick}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* CREATE WITH AI TAB */}
        {activeTab === 'create-ai' && (
          <div key="create-ai-tab" className="pt-2">
            <Card className="relative overflow-hidden">
              <CardWatermark opacity={2} scale={1} />
              <CardContent className="relative z-10 py-8">
                <CreateWithAI
                  onPolicyCreate={handlePolicyCreate}
                  onCancel={() => setActiveTab('policies')}
                />
              </CardContent>
            </Card>
          </div>
        )}

        {/* STRUCTURED BUILDER TAB */}
        {activeTab === 'structured' && (
          <div key="structured-tab" className="pt-2">
            <Card className="relative overflow-hidden">
              <CardWatermark opacity={2} scale={1} />
              <CardContent className="relative z-10 py-8">
                <div className="max-w-3xl mx-auto">
                  <div className="text-center mb-8">
                    <h2 className="text-xl font-bold text-brand-navy mb-2">
                      Structured Rule Builder
                    </h2>
                    <p className="text-muted-foreground">
                      Visually build rules with conditions and actions
                    </p>
                  </div>
                  <div className="mb-6">
                    <label className="block text-sm font-medium text-foreground mb-1.5">Rule Name *</label>
                    <input
                      type="text"
                      value={structuredName}
                      onChange={(e) => setStructuredName(e.target.value)}
                      placeholder="e.g., Auto-Approve Low Value Items"
                      className="w-full px-4 py-2.5 rounded-lg border border-gray-200 text-base focus:outline-none focus:ring-2 focus:ring-brand-cornflower/50"
                    />
                  </div>
                  <StructuredBuilder
                    onChange={(dsl) => setStructuredDSL(dsl)}
                  />
                  <div className="flex justify-center gap-3 mt-8">
                    <Button variant="ghost" onClick={() => setActiveTab('policies')}>
                      Cancel
                    </Button>
                    <Button
                      variant="gradient"
                      disabled={!structuredDSL || structuredDSL.conditions.length === 0 || !structuredName.trim() || isSavingStructured}
                      onClick={async () => {
                        if (!structuredDSL || !structuredName.trim()) return
                        setIsSavingStructured(true)
                        try {
                          await handlePolicyCreate({
                            name: structuredName.trim(),
                            description: '',
                            naturalLanguage: `Structured rule: ${structuredName}`,
                            policyType: 'logical',
                            dsl: {
                              conditions: structuredDSL.conditions.map(c => ({ field: c.field, operator: c.operator, value: c.value })),
                              actions: structuredDSL.actions.map(a => ({ type: a.type, value: a.value })),
                              match_mode: structuredDSL.match_mode,
                            },
                            refinedInstruction: null,
                            entityName: null,
                            tags: ['structured'],
                            priority: 50,
                          })
                          setStructuredName('')
                          setStructuredDSL(null)
                        } finally {
                          setIsSavingStructured(false)
                        }
                      }}
                    >
                      {isSavingStructured ? (
                        <><Icons.loader className="mr-2 h-4 w-4 animate-spin" />Saving...</>
                      ) : (
                        <><Icons.check className="mr-2 h-4 w-4" />Save Policy</>
                      )}
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* PERMISSION MATRIX TAB */}
        {activeTab === 'matrix' && (
          <div key="matrix-tab" className="pt-2">
            <PermissionMatrixTab />
          </div>
        )}
      </div>

      {/* Detail Modal - View only */}
      <PolicyDetailModal
        policy={selectedPolicy}
        isOpen={isDetailModalOpen}
        onClose={() => {
          setIsDetailModalOpen(false)
          setSelectedPolicy(null)
        }}
        onEdit={handleEditFromDetail}
        onToggleStatus={(id, isActive) => {
          togglePolicyStatus(id, isActive, null)
          setIsDetailModalOpen(false)
        }}
        onDelete={(id) => {
          deletePolicy(id)
          setIsDetailModalOpen(false)
        }}
      />

      {/* Edit Modal */}
      <PolicyEditModal
        policy={editingPolicy}
        isOpen={isEditModalOpen}
        onClose={() => {
          setIsEditModalOpen(false)
          setEditingPolicy(null)
        }}
        onSave={async (updatedPolicy) => {
            await togglePolicyStatus(updatedPolicy.id, !updatedPolicy.is_active, (updatedPolicy as any).value)
            setIsEditModalOpen(false)
            setEditingPolicy(null)
        }}
      />
    </div>
  )
}