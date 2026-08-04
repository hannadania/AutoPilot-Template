'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Icons } from '@/components/ui/icons'
import { cn } from '@/lib/utils'

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

interface Task {
  id?: number
  item_number: string
  operator_name: string
  proposed_action: string
  cost_impact: string
  jira_ticket_url: string
  status: string
}

export default function WorkbenchPage() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)

  const loadTasks = () => {
    setLoading(true)
    fetch('http://localhost:8001/api/webhooks/supervity/workbench')
      .then((res) => res.json())
      .then((data) => {
        setTasks(data.tasks || [])
      })
      .catch((err) => console.error('Error fetching tasks:', err))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadTasks()
  }, [])

  const handleApprove = (item_number: string) => {
    // Optimistically remove the task from the UI
    setTasks((prev) => prev.filter((t) => t.item_number !== item_number))
    
    // Put request to database
    fetch(`http://localhost:8001/api/webhooks/supervity/workbench/${item_number}/approve`, {
      method: 'PUT'
    }).catch(err => console.error("Failed to approve:", err))
    
    console.log(`Approved task for item: ${item_number}`)
  }

  return (
    <motion.div
      className='space-y-8'
      variants={containerVariants}
      initial='hidden'
      animate='visible'
    >
      {/* Header */}
      <motion.div variants={itemVariants} className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4">
        <div>
          <h1 className='text-display-3 font-bold tracking-tight text-brand-navy'>
            Human-in-the-Loop Workbench
          </h1>
          <p className='mt-2 text-lg text-muted-foreground'>
            Review and approve high-stakes exceptions caught by the AI Orchestrator.
          </p>
        </div>
        <Button variant="outline" onClick={loadTasks}>
          <Icons.activity className={cn("mr-2 h-4 w-4", loading ? "animate-spin" : "")} />
          Refresh Queue
        </Button>
      </motion.div>

      {/* Exception Queue */}
      <motion.div variants={itemVariants}>
        {loading ? (
           <div className="flex justify-center p-12">
             <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-cornflower border-t-transparent" />
           </div>
        ) : tasks.length === 0 ? (
          <Card className="border-dashed bg-slate-50/50">
            <CardContent className="flex flex-col items-center justify-center p-12 text-center">
              <div className="h-12 w-12 rounded-full bg-emerald-100 flex items-center justify-center mb-4">
                <Icons.zap className="h-6 w-6 text-emerald-600" />
              </div>
              <h3 className="text-lg font-semibold text-brand-navy">All Clear!</h3>
              <p className="text-muted-foreground max-w-sm mt-2">
                There are no pending exceptions. The AI is handling all automated workflows smoothly.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4">
            <AnimatePresence>
              {tasks.map((task) => (
                <motion.div
                  key={task.item_number}
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0, x: -20 }}
                >
                  <Card className="border-l-4 border-l-red-500 hover:shadow-md transition-all">
                    <CardHeader className="pb-3">
                      <div className="flex justify-between items-start">
                        <div>
                          <CardTitle className="text-red-600 flex items-center gap-2">
                            <Icons.zap className="h-5 w-5" />
                            Exception Alert: {task.item_number}
                          </CardTitle>
                          <CardDescription className="mt-1">
                            Flagged by <strong>{task.operator_name}</strong>
                          </CardDescription>
                        </div>
                        <span className="bg-red-100 text-red-700 text-xs font-bold px-3 py-1 rounded-full">
                          REQUIRES REVIEW
                        </span>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
                        <div className="space-y-2">
                          <p className="text-sm text-brand-navy">
                            <span className="font-semibold text-muted-foreground w-28 inline-block">Proposed Action:</span> 
                            {task.proposed_action}
                          </p>
                          <p className="text-sm text-brand-navy">
                            <span className="font-semibold text-muted-foreground w-28 inline-block">Cost Impact:</span> 
                            <span className="font-bold text-amber-600">{task.cost_impact}</span>
                          </p>
                        </div>
                        
                        <div className="flex gap-2">
                          <Button variant="outline" className="text-brand-navy" onClick={() => window.open(task.jira_ticket_url, '_blank')}>
                            <Icons.share className="mr-2 h-4 w-4" />
                            View Ticket
                          </Button>
                          <Button className="bg-emerald-600 hover:bg-emerald-700 text-white" onClick={() => handleApprove(task.item_number)}>
                            <Icons.arrowRight className="mr-2 h-4 w-4" />
                            Approve Action
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </motion.div>
    </motion.div>
  )
}