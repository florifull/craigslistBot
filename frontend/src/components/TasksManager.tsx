"use client";

import { useState, useEffect, useRef } from "react";
import { useSession } from "next-auth/react";
import { TaskStatus } from "@/types";
import {
  Plus,
  Edit,
  Trash2,
  Play,
  Pause,
  MapPin,
  Clock,
  Zap,
  ChevronDown,
  ChevronUp,
  FileText,
} from "lucide-react";
import { Task } from "@/types";
import {
  getUserTasks,
  deleteTask,
  toggleTaskActive,
  getTaskStatus,
} from "@/lib/api";

interface TasksManagerProps {
  onCreateTask: () => void;
  refreshTrigger?: number;
}

export function TasksManager({
  onCreateTask,
  refreshTrigger,
}: TasksManagerProps) {
  const { data: session } = useSession();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedLogs, setExpandedLogs] = useState<Set<string>>(new Set());
  const [taskStatuses, setTaskStatuses] = useState<Map<string, TaskStatus>>(
    new Map()
  );
  const tasksRef = useRef<Task[]>([]);

  // Function to determine if a task is currently running/scraping
  const isTaskCurrentlyRunning = (task: Task): boolean => {
    // Use real-time status if available
    const realtimeStatus = taskStatuses.get(task.id);
    if (realtimeStatus) {
      return realtimeStatus.status === "running";
    }

    // Fallback to log-based detection
    if (!task.logs || task.logs.length === 0) return false;

    // Get the most recent log entry
    const latestLog = task.logs[task.logs.length - 1];

    // Check if the latest log indicates completion
    const isCompleted =
      latestLog.message.toLowerCase().includes("completed") ||
      latestLog.message.toLowerCase().includes("found") ||
      latestLog.message.toLowerCase().includes("no listings") ||
      latestLog.message.toLowerCase().includes("no posts") ||
      latestLog.message.toLowerCase().includes("failed");

    // If completed, definitely not running
    if (isCompleted) return false;

    // Check if the latest log indicates active scraping
    const isScraping =
      latestLog.message.toLowerCase().includes("scraping") ||
      latestLog.message.toLowerCase().includes("running") ||
      latestLog.message.toLowerCase().includes("evaluating");

    // Only show as running if actively scraping and not completed
    return isScraping && !isCompleted;
  };

  // Load tasks from API
  useEffect(() => {
    const loadTasks = async () => {
      if (session?.user?.id) {
        setLoading(true);
        try {
          const userTasks = await getUserTasks(session.user.id);
          setTasks(userTasks);
          tasksRef.current = userTasks;
        } catch (error) {
          console.error("Failed to load tasks:", error);
        } finally {
          setLoading(false);
        }
      }
    };

    loadTasks();
  }, [session?.user?.id, refreshTrigger]);

  // Event-driven polling: only poll when tasks are running
  useEffect(() => {
    if (!session?.user?.id) return;

    let pollingInterval: NodeJS.Timeout | null = null;
    let checkInterval: NodeJS.Timeout | null = null;

    const pollTaskStatuses = async () => {
      if (!session?.user?.id || tasksRef.current.length === 0) return false;

      // Only poll active tasks that are currently running
      const activeTasks = tasksRef.current.filter((task) => task.is_active);
      let hasRunningTasks = false;

      for (const task of activeTasks) {
        try {
          const status = await getTaskStatus(task.id);
          if (status) {
            const previousStatus = taskStatuses.get(task.id);

            setTaskStatuses((prev) => new Map(prev).set(task.id, status));

            // Check if task is running
            if (status.status === "running") {
              hasRunningTasks = true;
            }

            // Refresh task data when status changes or when a recent completion is detected
            if (
              !previousStatus ||
              previousStatus.status !== status.status ||
              ((status as TaskStatus).recent && status.status === "completed")
            ) {
              // Task status changed or recent completion detected - refresh data to get updated metrics and logs
              await refreshTaskData(task.id);
            }
          }
        } catch (error) {
          console.error(`Failed to get status for task ${task.id}:`, error);
        }
      }

      return hasRunningTasks;
    };

    const startPolling = async () => {
      // Don't start if already polling
      if (pollingInterval) return;

      // First check if any tasks are currently running based on logs (without making API calls)
      const activeTasks = tasksRef.current.filter((task) => task.is_active);
      const hasRunningTasks = activeTasks.some((task) => {
        const realtimeStatus = taskStatuses.get(task.id);
        if (realtimeStatus && realtimeStatus.status === "running") {
          return true;
        }

        // Check logs for running status
        if (!task.logs || task.logs.length === 0) return false;
        const latestLog = task.logs[task.logs.length - 1];
        const isScraping =
          latestLog.message.toLowerCase().includes("scraping") ||
          latestLog.message.toLowerCase().includes("running") ||
          latestLog.message.toLowerCase().includes("evaluating");
        const isCompleted =
          latestLog.message.toLowerCase().includes("completed") ||
          latestLog.message.toLowerCase().includes("found") ||
          latestLog.message.toLowerCase().includes("no listings") ||
          latestLog.message.toLowerCase().includes("no posts") ||
          latestLog.message.toLowerCase().includes("failed");

        return isScraping && !isCompleted;
      });

      // Also check if any tasks have recent completions that need polling
      const hasRecentCompletions = activeTasks.some((task) => {
        const realtimeStatus = taskStatuses.get(task.id);
        return (
          realtimeStatus &&
          realtimeStatus.recent &&
          realtimeStatus.status === "completed"
        );
      });

      // If we have active tasks, always start polling to check for updates
      // This ensures we catch recent completions even if taskStatuses is empty initially
      if (hasRunningTasks || hasRecentCompletions || activeTasks.length > 0) {
        console.log("Starting polling for running tasks or recent completions");
        // Continue polling every 3 seconds while tasks are running or have recent completions
        pollingInterval = setInterval(async () => {
          const stillRunning = await pollTaskStatuses();
          if (!stillRunning) {
            console.log("Stopping polling - no running tasks");
            if (pollingInterval) {
              clearInterval(pollingInterval);
              pollingInterval = null;
            }
          }
        }, 3000);
      }
    };

    const stopPolling = () => {
      if (pollingInterval) {
        console.log("Stopping polling");
        clearInterval(pollingInterval);
        pollingInterval = null;
      }
    };

    // Initial check and start polling if needed
    startPolling();

    // Check periodically (every 30 seconds) to detect when tasks start running
    checkInterval = setInterval(startPolling, 30000);

    return () => {
      stopPolling();
      if (checkInterval) {
        clearInterval(checkInterval);
      }
    };
  }, [session?.user?.id]);

  // Event-driven refresh: only refresh when a task actually runs
  const refreshTaskData = async (taskId: string) => {
    if (!session?.user?.id) return;

    try {
      // Refresh all tasks to get updated metrics and logs for the specific task
      const userTasks = await getUserTasks(session.user.id);
      setTasks(userTasks);
      tasksRef.current = userTasks;
    } catch (error) {
      console.error("Failed to refresh task data:", error);
    }
  };

  // Refresh tasks when a new task is created
  const handleTaskCreated = async () => {
    if (session?.user?.id) {
      try {
        const userTasks = await getUserTasks(session.user.id);
        setTasks(userTasks);
        tasksRef.current = userTasks;
      } catch (error) {
        console.error("Failed to refresh tasks:", error);
      }
    }
  };

  const handleToggleTask = async (taskId: string) => {
    if (!session?.user?.id) return;

    const task = tasks.find((t) => t.id === taskId);
    if (!task) return;

    const success = await toggleTaskActive(
      taskId,
      session.user.id,
      !task.is_active
    );
    if (success) {
      setTasks(
        tasks.map((t) =>
          t.id === taskId ? { ...t, is_active: !t.is_active } : t
        )
      );
    }
  };

  const handleDeleteTask = async (taskId: string) => {
    if (!session?.user?.id) return;

    if (confirm("Are you sure you want to delete this monitoring task?")) {
      const success = await deleteTask(taskId, session.user.id);
      if (success) {
        setTasks(tasks.filter((task) => task.id !== taskId));
      }
    }
  };

  const toggleLogs = (taskId: string) => {
    const newExpanded = new Set(expandedLogs);
    if (newExpanded.has(taskId)) {
      newExpanded.delete(taskId);
    } else {
      newExpanded.add(taskId);
    }
    setExpandedLogs(newExpanded);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-white">Monitoring Tasks</h2>
        <button
          onClick={() => onCreateTask()}
          className="btn-primary flex items-center gap-2"
        >
          <Plus className="w-5 h-5" />
          Create Task
        </button>
      </div>

      {loading ? (
        <div className="text-center py-12">
          <div className="w-16 h-16 bg-white/5 rounded-xl mx-auto mb-4 flex items-center justify-center">
            <div className="w-6 h-6 border-2 border-white/20 border-t-white rounded-full animate-spin"></div>
          </div>
          <p className="text-white/60">Loading tasks...</p>
        </div>
      ) : tasks.length === 0 ? (
        <div className="text-center py-12">
          <div className="w-16 h-16 bg-white/5 rounded-xl mx-auto mb-4 flex items-center justify-center">
            <Zap className="w-8 h-8 text-white/20" />
          </div>
          <h3 className="text-lg font-semibold text-white mb-2">
            No monitoring tasks yet
          </h3>
          <p className="text-white/60 mb-6">
            Create your first task to start monitoring Craigslist listings
          </p>
          <button onClick={onCreateTask} className="btn-primary">
            Create First Task
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {tasks.map((task) => (
            <div key={task.id} className="card">
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-white mb-2">
                    {task.name}
                  </h3>
                  <p className="text-white/60 text-sm mb-3">
                    {task.description}
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleToggleTask(task.id)}
                    className={`p-2 rounded-lg transition-colors ${
                      task.is_active
                        ? "bg-green-500/20 text-green-400 hover:bg-green-500/30"
                        : "bg-gray-500/20 text-gray-400 hover:bg-gray-500/30"
                    }`}
                  >
                    {task.is_active ? (
                      <Pause className="w-4 h-4" />
                    ) : (
                      <Play className="w-4 h-4" />
                    )}
                  </button>
                  <button className="p-2 bg-white/5 hover:bg-white/10 rounded-lg text-white/60 hover:text-white transition-colors">
                    <Edit className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDeleteTask(task.id)}
                    className="p-2 bg-red-500/20 hover:bg-red-500/30 rounded-lg text-red-400 hover:text-red-300 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Task Details */}
              <div className="space-y-3 text-sm">
                <div className="flex items-center gap-2 text-white/80">
                  <MapPin className="w-4 h-4" />
                  <span>
                    {task.location} • {task.distance} miles
                  </span>
                </div>

                <div className="flex items-center gap-2 text-white/80">
                  <Clock className="w-4 h-4" />
                  <span>
                    Every{" "}
                    {task.frequency_minutes >= 60
                      ? `${Math.floor(task.frequency_minutes / 60)} hour${
                          Math.floor(task.frequency_minutes / 60) > 1 ? "s" : ""
                        }`
                      : `${task.frequency_minutes} minute${
                          task.frequency_minutes > 1 ? "s" : ""
                        }`}
                  </span>
                </div>

                <div className="flex items-center gap-2 text-white/80">
                  <Zap className="w-4 h-4" />
                  <span>{task.strictness.replace("_", " ")} filtering</span>
                </div>

                <div className="flex items-center gap-2 text-white/60">
                  <Clock className="w-4 h-4" />
                  <span>
                    Cooldown until:{" "}
                    {task.next_cooldown
                      ? (() => {
                          // Handle both Unix timestamps and ISO strings for next_cooldown
                          const nextCooldown = task.next_cooldown;
                          if (typeof nextCooldown === "number") {
                            return new Date(
                              nextCooldown * 1000
                            ).toLocaleString();
                          } else if (typeof nextCooldown === "string") {
                            return new Date(nextCooldown).toLocaleString();
                          }
                          return "Unknown";
                        })()
                      : task.last_run
                      ? (() => {
                          // Handle both Unix timestamps and ISO strings for last_run
                          const lastRun = task.last_run;
                          let lastRunTime;
                          if (typeof lastRun === "number") {
                            lastRunTime = new Date(lastRun * 1000).getTime();
                          } else if (typeof lastRun === "string") {
                            lastRunTime = new Date(lastRun).getTime();
                          } else {
                            return "Starting soon";
                          }
                          return new Date(
                            lastRunTime + task.frequency_minutes * 60000
                          ).toLocaleString();
                        })()
                      : "Starting soon"}
                  </span>
                </div>
              </div>

              {/* Stats */}
              <div className="mt-4 pt-4 border-t border-white/10">
                <div className="flex justify-between text-sm">
                  <span className="text-white/60">
                    Runs: {task.total_runs || 0}
                  </span>
                  <span className="text-blue-400">
                    Scrapes: {task.total_scrapes || 0}
                  </span>
                  <span className="text-green-400">
                    Matches: {task.total_matches || 0}
                  </span>
                  <span className="text-white/60">
                    Rate:{" "}
                    {task.total_scrapes > 0
                      ? (
                          (task.total_matches / task.total_scrapes) *
                          100
                        ).toFixed(1)
                      : 0}
                    %
                  </span>
                </div>
                {task.last_run && (
                  <div className="text-xs text-white/50 mt-2">
                    Last run:{" "}
                    {(() => {
                      // Handle both Unix timestamps and ISO strings
                      const lastRun = task.last_run;
                      if (typeof lastRun === "number") {
                        // Unix timestamp in seconds, convert to milliseconds
                        return new Date(lastRun * 1000).toLocaleString();
                      } else if (typeof lastRun === "string") {
                        // ISO string
                        return new Date(lastRun).toLocaleString();
                      }
                      return "Unknown";
                    })()}
                  </div>
                )}
              </div>

              {/* Status */}
              <div className="mt-4 flex items-center gap-2">
                <div
                  className={`w-2 h-2 rounded-full ${
                    task.is_active ? "bg-green-400" : "bg-gray-400"
                  }`}
                ></div>
                <span
                  className={`text-xs font-medium ${
                    task.is_active ? "text-green-400" : "text-gray-400"
                  }`}
                >
                  {task.is_active ? "Active Monitoring" : "Paused"}
                </span>
                {/* Scraping animation only for tasks currently running */}
                {task.is_active && isTaskCurrentlyRunning(task) && (
                  <div className="flex items-center gap-1 ml-2">
                    <div className="flex gap-1">
                      <div className="w-1 h-1 bg-blue-400 rounded-full animate-pulse"></div>
                      <div
                        className="w-1 h-1 bg-blue-400 rounded-full animate-pulse"
                        style={{ animationDelay: "0.2s" }}
                      ></div>
                      <div
                        className="w-1 h-1 bg-blue-400 rounded-full animate-pulse"
                        style={{ animationDelay: "0.4s" }}
                      ></div>
                    </div>
                    <span className="text-xs text-blue-400">Scraping...</span>
                  </div>
                )}
              </div>

              {/* Logs Section */}
              <div className="mt-4 pt-4 border-t border-white/10">
                <button
                  onClick={() => toggleLogs(task.id)}
                  className="flex items-center gap-2 text-sm text-white/60 hover:text-white/80 transition-colors"
                >
                  <FileText className="w-4 h-4" />
                  <span>Logs</span>
                  {expandedLogs.has(task.id) ? (
                    <ChevronUp className="w-4 h-4" />
                  ) : (
                    <ChevronDown className="w-4 h-4" />
                  )}
                </button>

                {expandedLogs.has(task.id) && (
                  <div className="mt-3 bg-white/5 rounded-lg p-3 max-h-48 overflow-y-auto">
                    {task.logs && task.logs.length > 0 ? (
                      <div className="space-y-2">
                        {task.logs.map((log, index) => (
                          <div
                            key={index}
                            className={`text-xs p-2 rounded ${
                              log.level === "error"
                                ? "bg-red-500/10 text-red-400"
                                : log.level === "warning"
                                ? "bg-yellow-500/10 text-yellow-400"
                                : log.level === "success"
                                ? "bg-green-500/10 text-green-400"
                                : "bg-white/5 text-white/80"
                            }`}
                          >
                            <div className="flex items-center gap-2">
                              <span className="text-white/50">
                                {new Date(log.timestamp).toLocaleString()}
                              </span>
                              <span className="font-medium">{log.message}</span>
                              {/* Show scraping animation for running logs */}
                              {log.message.includes("Scraping") && (
                                <div className="flex items-center gap-1">
                                  <div className="flex gap-1">
                                    <div className="w-1 h-1 bg-blue-400 rounded-full animate-pulse"></div>
                                    <div
                                      className="w-1 h-1 bg-blue-400 rounded-full animate-pulse"
                                      style={{ animationDelay: "0.2s" }}
                                    ></div>
                                    <div
                                      className="w-1 h-1 bg-blue-400 rounded-full animate-pulse"
                                      style={{ animationDelay: "0.4s" }}
                                    ></div>
                                  </div>
                                </div>
                              )}
                            </div>
                            {log.details && (
                              <div className="mt-1 text-white/60">
                                {typeof log.details === "string"
                                  ? log.details
                                  : JSON.stringify(log.details, null, 2)}
                              </div>
                            )}
                          </div>
                        ))}
                        {/* Show current scraping status only if task is currently running */}
                        {task.is_active && isTaskCurrentlyRunning(task) && (
                          <div className="text-xs p-2 rounded bg-blue-500/10 text-blue-400">
                            <div className="flex items-center gap-2">
                              <span className="text-white/50">
                                {new Date().toLocaleString()}
                              </span>
                              <span className="font-medium">
                                Currently scraping...
                              </span>
                              <div className="flex gap-1">
                                <div className="w-1 h-1 bg-blue-400 rounded-full animate-pulse"></div>
                                <div
                                  className="w-1 h-1 bg-blue-400 rounded-full animate-pulse"
                                  style={{ animationDelay: "0.2s" }}
                                ></div>
                                <div
                                  className="w-1 h-1 bg-blue-400 rounded-full animate-pulse"
                                  style={{ animationDelay: "0.4s" }}
                                ></div>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="text-xs text-white/50 text-center py-4">
                        No logs available yet. Logs will appear after the first
                        execution.
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
