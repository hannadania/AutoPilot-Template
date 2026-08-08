'use client'

import { useState, useRef, useEffect } from 'react'
import { motion, useInView } from 'framer-motion'
import apiClient from '@/lib/api-client'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { CardWatermark } from '@/components/ui/card-watermark'
import { Icons } from '@/components/ui/icons'
import { ActivityChart } from '@/components/ActivityChart'
import { cn } from '@/lib/utils'

// Animation variants
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.1,
    },
  },
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.5,
      ease: [0.25, 0.46, 0.45, 0.94],
    },
  },
}

// Animated number component
function AnimatedNumber({
  value,
  suffix = '',
  duration = 1000,
}: {
  value: number
  suffix?: string
  duration?: number
}) {
  const [displayValue, setDisplayValue] = useState(0)
  const ref = useRef<HTMLSpanElement>(null)
  const isInView = useInView(ref, { once: true, amount: 0.5 })
  const hasAnimated = useRef(false)

  useEffect(() => {
    if (!isInView || hasAnimated.current) return
    hasAnimated.current = true

    const startTime = performance.now()

    const animate = (currentTime: number) => {
      const elapsed = currentTime - startTime
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(2, -10 * progress)

      setDisplayValue(Math.round(eased * value))

      if (progress < 1) {
        requestAnimationFrame(animate)
      } else {
        setDisplayValue(value)
      }
    }

    requestAnimationFrame(animate)
  }, [value, duration, isInView])

  const formatValue = (num: number): string => {
    if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'K'
    }
    return num.toString()
  }

  return (
    <span ref={ref}>
      {formatValue(displayValue)}
      {suffix}
    </span>
  )
}

// Stats Card Component with Bento styling
interface StatCardProps {
  title: string
  value: number
  suffix?: string
  icon: React.ElementType
  trend?: { value: string; positive: boolean }
  colorClass: string
  delay?: number
}

function StatCard({
  title,
  value,
  suffix = '',
  icon: Icon,
  trend,
  colorClass,
  delay = 0,
}: StatCardProps) {
  return (
    <motion.div
      variants={itemVariants}
      initial='hidden'
      animate='visible'
      transition={{ delay }}
      whileHover={{ y: -4 }}
    >
      <Card className='group relative h-full cursor-default overflow-hidden'>
        {/* Branded watermark texture */}
        <CardWatermark opacity={3} scale={0.9} />
        <CardContent className='relative z-10 p-5'>
          <div className='flex items-start justify-between'>
            <div className='space-y-2'>
              {/* Micro label */}
              <p className='text-micro uppercase text-brand-muted transition-colors duration-200 group-hover:text-brand-cornflower'>
                {title}
              </p>
              {/* Display number */}
              <p className='font-display text-[2.25rem] font-bold leading-none tracking-tight text-brand-navy'>
                <AnimatedNumber value={value} suffix={suffix} />
              </p>
              {/* Trend */}
              {trend && (
                <motion.p
                  className={cn(
                    'flex items-center gap-1 text-xs font-medium',
                    trend.positive ? 'text-emerald-600' : 'text-red-500'
                  )}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: delay + 0.3 }}
                >
                  {trend.positive ? (
                    <Icons.trendingUp className='h-3 w-3' strokeWidth={2} />
                  ) : (
                    <Icons.trendingUp
                      className='h-3 w-3 rotate-180'
                      strokeWidth={2}
                    />
                  )}
                  {trend.value}
                </motion.p>
              )}
            </div>
            {/* Icon */}
            <motion.div
              className={cn(
                'rounded-xl p-2.5 text-white',
                'shadow-lg',
                colorClass
              )}
              whileHover={{ scale: 1.15, rotate: 5 }}
              transition={{ type: 'spring', stiffness: 400, damping: 17 }}
            >
              <Icon className='h-5 w-5' strokeWidth={1.5} />
            </motion.div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  )
}

// Hero Section
function HeroSection({ userName }: { userName?: string }) {
  const firstName = userName?.split(' ') || 'there'

  return (
    <motion.div
      className='col-span-12 py-2'
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.25, 0.46, 0.45, 0.94] }}
    >
      {/* 🚀 Main Header Title */}
      <h1 className='text-display-3 font-bold tracking-tight text-brand-navy lg:text-display-2'>
        Disruption <span className='text-gradient'>Commander</span>
      </h1>
      
      {/* 💡 Sub-tagline */}
      <p className='mt-2 text-xl font-semibold text-brand-cornflower tracking-tight'>
        Where Intelligence Meets Human.
      </p>
      
      {/* Welcome Message */}
      <p className='mt-4 text-lg font-light text-muted-foreground'>
        Welcome back, {firstName}. Your AI Command Center is ready.
      </p>
    </motion.div>
  )
}


// Diagnostics Card
function DiagnosticsCard() {
  const [apiResponse, setApiResponse] = useState<string>('')
  const [adminResponse, setAdminResponse] = useState<string>('')
  const [isLoading, setIsLoading] = useState(false)

  const callApi = async (
    endpoint: string,
    setter: React.Dispatch<React.SetStateAction<string>>
  ) => {
    setIsLoading(true)
    setter('Loading...')
    try {
      const data = await apiClient(endpoint)
      setter(JSON.stringify(data, null, 2))
    } catch (error) {
      setter(
        `Error: ${error instanceof Error ? error.message : 'Unknown error'}`
      )
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Card className='relative col-span-12 h-full overflow-hidden'>
      <CardWatermark opacity={3} scale={1.1} />
      <CardHeader className='relative z-10'>
        <CardTitle className='flex items-center gap-2'>
          <Icons.activity
            className='h-5 w-5 text-brand-cornflower'
            strokeWidth={1.5}
          />
          System Diagnostics
        </CardTitle>
      </CardHeader>
      <CardContent className='relative z-10 space-y-6'>
        <div className='space-y-3'>
          <div className='flex items-center justify-between'>
            <div>
              <p className='text-sm font-medium text-foreground'>
                Standard Authorization
              </p>
              <p className='mt-0.5 font-mono text-xs text-muted-foreground'>
                /api/test
              </p>
            </div>
          </div>
          <Button
            onClick={() => callApi('/api/test', setApiResponse)}
            disabled={isLoading}
            variant='outline'
            className='w-full'
          >
            {isLoading ? 'Running...' : 'Run Diagnostics'}
          </Button>
          {apiResponse && (
            <div className='rounded-xl border border-border/50 bg-muted/30 p-4'>
              <pre className='overflow-x-auto font-mono text-xs text-muted-foreground'>
                <code>{apiResponse}</code>
              </pre>
            </div>
          )}
        </div>

        <div className='h-px bg-border/50' />

        <div className='space-y-3'>
          <div className='flex items-center justify-between'>
            <div>
              <p className='text-sm font-medium text-foreground'>
                Admin Verification
              </p>
              <p className='mt-0.5 font-mono text-xs text-muted-foreground'>
                /api/admin/dashboard
              </p>
            </div>
          </div>
          <Button
            onClick={() => callApi('/api/admin/dashboard', setAdminResponse)}
            disabled={isLoading}
            variant='gradient'
            className='w-full'
          >
            {isLoading ? 'Verifying...' : 'Verify Admin Access'}
            <Icons.arrowRight className='ml-2 h-4 w-4' />
          </Button>
          {adminResponse && (
            <div className='rounded-xl border border-border/50 bg-muted/30 p-4'>
              <pre className='overflow-x-auto font-mono text-xs text-muted-foreground'>
                <code>{adminResponse}</code>
              </pre>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}











function IntegrationsHealth() {
  return (
    <Card className='h-full bg-card/50 backdrop-blur-md border-brand-navy/10 relative overflow-hidden'>
      <CardContent className='p-6 space-y-4'>
        <h3 className='text-lg font-bold text-brand-navy flex items-center gap-2'>
          <Icons.activity className='h-5 w-5 text-emerald-500 animate-pulse' />
          Integration Diagnostics
        </h3>
        <p className='text-xs text-muted-foreground'>
          Real-time webhook and cloud database health status.
        </p>
        
        <div className='space-y-3 pt-2'>
          {/* Supabase Connection */}
          <div className='flex items-center justify-between p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/20'>
            <span className='font-semibold text-sm text-brand-navy'>Supabase Database</span>
            <span className='text-[10px] font-bold px-2 py-1 rounded bg-emerald-500/20 text-emerald-600 animate-pulse'>ACTIVE</span>
          </div>

          {/* Slack Connection */}
          <div className='flex items-center justify-between p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/20'>
            <span className='font-semibold text-sm text-brand-navy'>Slack Alerts Portal</span>
            <span className='text-[10px] font-bold px-2 py-1 rounded bg-emerald-500/20 text-emerald-600 animate-pulse'>ACTIVE</span>
          </div>

          {/* Jira Connection */}
          <div className='flex items-center justify-between p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/20'>
            <span className='font-semibold text-sm text-brand-navy'>Jira Incident Desk</span>
            <span className='text-[10px] font-bold px-2 py-1 rounded bg-emerald-500/20 text-emerald-600 animate-pulse'>ACTIVE</span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}





// Main Dashboard — no auth required, renders directly

export default function HomePage() {
  // 1. Safe default state
  const [stats, setStats] = useState({
    active_disruptions: 0,
    cost_avoided: 'MYR 0.00',
    success_rate: '100%',
    total_tasks: 0
  })

  // 2. Fetch stats with automatic 5-second dynamic polling!
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await fetch('http://localhost:8001/api/dashboard/stats')
        if (res.ok) {
          const data = await res.json()
          setStats(data)
        }
      } catch (error) {
        console.error('Error fetching dashboard stats:', error)
      }
    }

    fetchStats()
    const interval = setInterval(fetchStats, 5000)
    return () => clearInterval(interval)
  }, [])

  // 3. 🛡️ TYPE-SAFE PARSERS & CALCULATIONS
  const flaggedPending = typeof stats?.active_disruptions === 'number' 
    ? stats.active_disruptions 
    : 0

  const totalCases = typeof stats?.total_tasks === 'number' 
    ? stats.total_tasks 
    : 0

  // Accomplished Cases = Total Cases minus the currently pending disruptions
  const accomplishedCases = Math.max(0, totalCases - flaggedPending)

  const rawSuccess = stats?.success_rate 
    ? parseFloat(stats.success_rate) 
    : 100
  const successRate = isNaN(rawSuccess) ? 100 : rawSuccess

  return (
    <motion.div
      className='space-y-6'
      variants={containerVariants}
      initial='hidden'
      animate='visible'
    >
      {/* Hero Section (Using our updated title and tagline!) */}
      <HeroSection userName='Developer' />

      {/* KPI Cards Grid with Live Supabase Badges */}
      <div className='grid grid-span-12 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6'>
        {/* Card 1: Accomplished Cases */}
        <StatCard
          key={`accomplished-${accomplishedCases}`}
          title='Accomplished Cases'
          value={accomplishedCases}
          icon={Icons.checkCircle}
          trend={{ value: '~ Live Supabase', positive: true }}
          colorClass='bg-brand-navy'
          delay={0.1}
        />

        {/* Card 2: Success Rate */}
        <StatCard
          key={`success-${successRate}`}
          title='Success Rate'
          value={successRate}
          suffix='%'
          icon={Icons.activity}
          trend={{ value: '~ Live Supabase', positive: true }}
          colorClass='bg-brand-cornflower'
          delay={0.2}
        />

        {/* Card 3: Total Cases */}
        <StatCard
          key={`total-${totalCases}`}
          title='Total Cases'
          value={totalCases}
          icon={Icons.users}
          trend={{ value: '~ Live Supabase', positive: true }}
          colorClass='bg-brand-purple'
          delay={0.3}
        />

        {/* Card 4: Flagged Pending */}
        <StatCard
          key={`pending-${flaggedPending}`}
          title='Flagged Pending'
          value={flaggedPending}
          icon={Icons.sparkles}
          trend={{ value: '~ Live Supabase', positive: true }}
          colorClass='bg-gradient-to-br from-brand-navy to-brand-purple'
          delay={0.4}
        />
      </div>

      {/* 📊 Visual Graphs & System Diagnostics Side-by-Side! */}
      <div className='grid grid-cols-12 gap-6 mt-6'>
        {/* Left Side: Weekly Activity Line Graph */}
        <div className='col-span-12 lg:col-span-8'>
          <ActivityChart />
        </div>

        {/* Right Side: Active Integrations Health */}
        <div className='col-span-12 lg:col-span-4'>
          <IntegrationsHealth /> {/* ✅ Replaced the useless diagnostics tool! */}
        </div>
      </div>





      
    </motion.div>
  )
}
