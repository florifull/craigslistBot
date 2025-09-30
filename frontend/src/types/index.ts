export interface User {
  id: string
  email: string
  name: string
  avatar?: string
  createdAt: Date
}

export interface TaskLog {
  timestamp: string
  message: string
  level: 'info' | 'success' | 'warning' | 'error'
  details?: any
}

export interface Task {
  id: string
  user_id: string
  name: string
  description: string
  location: string
  distance: number
  frequency_minutes: number
  discord_webhook_url: string
  strictness: 'less_strict' | 'strict' | 'very_strict'
  is_active: boolean
  created_at: string
  last_run?: string | number
  next_cooldown?: string | number
  total_runs: number
  total_scrapes: number
  total_matches: number
  logs?: TaskLog[]
}

export interface ScrapingMetrics {
  totalTasks: number
  activeMonitoring: number
  totalScrapes: number
  totalMatches: number
  avgMatchesPerScan: number
  lastActivity: Date
}

export interface ScrapingResult {
  id: string
  taskId: string
  timestamp: Date
  listingsFound: number
  matchesFound: number
  executionTimeMs: number
  success: boolean
  error?: string
}

export interface TaskStatus {
  status: string
  message?: string
  recent?: boolean
}
