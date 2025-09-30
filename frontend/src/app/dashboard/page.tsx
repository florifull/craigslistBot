"use client";

import { useState } from "react";
import { DashboardHeader } from "@/components/DashboardHeader";
import { MetricsOverview } from "@/components/MetricsOverview";
import { TasksManager } from "@/components/TasksManager";
import { CreateTaskModal } from "@/components/CreateTaskModal";
import { RecentActivity } from "@/components/RecentActivity";

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState<"overview" | "tasks" | "metrics">(
    "overview"
  );
  const [showCreateTask, setShowCreateTask] = useState(false);
  const [refreshTasks, setRefreshTasks] = useState(0);

  return (
    <div className="min-h-screen bg-dark-900">
      <DashboardHeader />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Tab Navigation */}
        <div className="border-b border-white/10 mb-8">
          <nav className="-mb-px flex space-x-8">
            {[
              { id: "overview", name: "Overview", icon: "📊" },
              { id: "tasks", name: "Tasks", icon: "⚡" },
              { id: "metrics", name: "Metrics", icon: "📈" },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors flex items-center gap-2 ${
                  activeTab === tab.id
                    ? "border-primary-500 text-primary-400"
                    : "border-transparent text-white/60 hover:text-white/80"
                }`}
              >
                <span>{tab.icon}</span>
                {tab.name}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        {activeTab === "overview" && (
          <div className="space-y-8">
            <MetricsOverview />
            <RecentActivity />
          </div>
        )}

        {activeTab === "tasks" && (
          <TasksManager
            onCreateTask={() => setShowCreateTask(true)}
            refreshTrigger={refreshTasks}
          />
        )}

        {activeTab === "metrics" && (
          <div className="space-y-8">
            <MetricsOverview />
            <RecentActivity />
          </div>
        )}
      </div>

      {/* Create Task Modal */}
      {showCreateTask && (
        <CreateTaskModal
          onClose={() => setShowCreateTask(false)}
          onTaskCreated={() => {
            setShowCreateTask(false);
            setRefreshTasks((prev) => prev + 1); // Trigger refresh
          }}
        />
      )}
    </div>
  );
}
