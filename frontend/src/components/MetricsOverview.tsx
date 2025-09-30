"use client";

import { Activity, Target, Clock, Zap } from "lucide-react";

export function MetricsOverview() {
  // Mock metrics data - replace with real API calls
  const metrics = {
    totalTasks: 5,
    activeMonitoring: 3,
    totalScrapes: 1247,
    totalMatches: 23,
    sessionsToday: 47,
    avgResponseTime: "2.3s",
  };

  return (
    <div>
      <h2 className="text-2xl font-bold text-white mb-6">
        Performance Overview
      </h2>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Active Monitoring */}
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-white/60 text-sm font-medium">
                Active Monitoring
              </p>
              <p className="text-3xl font-bold text-white">
                {metrics.activeMonitoring}
              </p>
              <p className="text-xs text-green-400 mt-1">
                <Clock className="w-3 h-3 inline mr-1" />
                60% of tasks
              </p>
            </div>
            <div className="p-3 bg-green-500/20 rounded-lg">
              <Activity className="w-6 h-6 text-green-400" />
            </div>
          </div>
        </div>

        {/* Total Scrapes */}
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-white/60 text-sm font-medium">Total Scrapes</p>
              <p className="text-3xl font-bold text-white">
                {metrics.totalScrapes.toLocaleString()}
              </p>
              <p className="text-xs text-blue-400 mt-1">+12% from last week</p>
            </div>
            <div className="p-3 bg-blue-500/20 rounded-lg">
              <Zap className="w-6 h-6 text-blue-400" />
            </div>
          </div>
        </div>

        {/* Total Matches */}
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-white/60 text-sm font-medium">
                Quality Matches
              </p>
              <p className="text-3xl font-bold text-white">
                {metrics.totalMatches}
              </p>
              <p className="text-xs text-purple-400 mt-1">1.8% hit rate</p>
            </div>
            <div className="p-3 bg-purple-500/20 rounded-lg">
              <Target className="w-6 h-6 text-purple-400" />
            </div>
          </div>
        </div>

        {/* Sessions Today */}
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-white/60 text-sm font-medium">Scans Today</p>
              <p className="text-3xl font-bold text-white">
                {metrics.sessionsToday}
              </p>
              <p className="text-xs text-yellow-400 mt-1">
                Every 30 minutes avg
              </p>
            </div>
            <div className="p-3 bg-yellow-500/20 rounded-lg">
              <Clock className="w-6 h-6 text-yellow-400" />
            </div>
          </div>
        </div>

        {/* Response Time */}
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-white/60 text-sm font-medium">Avg Response</p>
              <p className="text-3xl font-bold text-white">
                {metrics.avgResponseTime}
              </p>
              <p className="text-xs text-emerald-400 mt-1">Very fast</p>
            </div>
            <div className="p-3 bg-emerald-500/20 rounded-lg">
              <Zap className="w-6 h-6 text-emerald-400" />
            </div>
          </div>
        </div>

        {/* Total Tasks */}
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-white/60 text-sm font-medium">Total Tasks</p>
              <p className="text-3xl font-bold text-white">
                {metrics.totalTasks}
              </p>
              <p className="text-xs text-indigo-400 mt-1">3 new this month</p>
            </div>
            <div className="p-3 bg-indigo-500/20 rounded-lg">
              <Activity className="w-6 h-6 text-indigo-400" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
