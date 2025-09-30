"use client";

import { useState } from "react";
import { Activity, Clock, CheckCircle, XCircle, Zap } from "lucide-react";

interface ActivityItem {
  id: string;
  taskName: string;
  timestamp: Date;
  type: "success" | "found" | "error";
  message: string;
  listings?: number;
  matches?: number;
}

export function RecentActivity() {
  const [activities] = useState<ActivityItem[]>([
    {
      id: "1",
      taskName: "Road Bike 54cm",
      timestamp: new Date("2025-09-29T03:15:00Z"),
      type: "found",
      message: "Found 3 new matches!",
      listings: 12,
      matches: 3,
    },
    {
      id: "2",
      taskName: "MacBook Pro M3",
      timestamp: new Date("2025-09-29T02:45:00Z"),
      type: "success",
      message: "Scan completed successfully",
      listings: 8,
      matches: 1,
    },
    {
      id: "3",
      taskName: "Road Bike 54cm",
      timestamp: new Date("2025-09-29T01:15:00Z"),
      type: "success",
      message: "Scan completed - no matches",
      listings: 15,
      matches: 0,
    },
    {
      id: "4",
      taskName: "MacBook Pro M3",
      timestamp: new Date("2025-09-29T00:45:00Z"),
      type: "error",
      message: "Temporary network error - retried successfully",
    },
    {
      id: "5",
      taskName: "Road Bike 54cm",
      timestamp: new Date("2025-09-29T00:15:00Z"),
      type: "found",
      message: "Found 1 new match!",
      listings: 11,
      matches: 1,
    },
  ]);

  const getIcon = (type: ActivityItem["type"]) => {
    switch (type) {
      case "success":
        return <CheckCircle className="w-4 h-4 text-green-400" />;
      case "found":
        return <Zap className="w-4 h-4 text-blue-400" />;
      case "error":
        return <XCircle className="w-4 h-4 text-red-400" />;
    }
  };

  const getBgColor = (type: ActivityItem["type"]) => {
    switch (type) {
      case "success":
        return "bg-green-500/10 border-green-500/20";
      case "found":
        return "bg-blue-500/10 border-blue-500/20";
      case "error":
        return "bg-red-500/10 border-red-500/20";
    }
  };

  return (
    <div>
      <h2 className="text-2xl font-bold text-white mb-6">Recent Activity</h2>

      <div className="card">
        <div className="space-y-4">
          {activities.map((activity) => (
            <div
              key={activity.id}
              className={`flex items-start gap-4 p-4 rounded-lg border ${getBgColor(
                activity.type
              )}`}
            >
              <div className="flex-shrink-0 mt-1">{getIcon(activity.type)}</div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-medium text-white truncate">
                    {activity.taskName}
                  </h4>
                  <div className="flex items-center gap-2 text-xs text-white/60">
                    <Clock className="w-3 h-3" />
                    <time>{activity.timestamp.toLocaleString()}</time>
                  </div>
                </div>

                <p className="text-sm text-white/80 mt-1">{activity.message}</p>

                {activity.listings !== undefined && (
                  <div className="flex items-center gap-4 mt-2 text-xs text-white/60">
                    <span>Listings: {activity.listings}</span>
                    {activity.matches !== undefined && (
                      <span>Matches: {activity.matches}</span>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-6 pt-4 border-t border-white/10">
          <button className="text-sm text-primary-400 hover:text-primary-300 transition-colors">
            View all activity →
          </button>
        </div>
      </div>
    </div>
  );
}
