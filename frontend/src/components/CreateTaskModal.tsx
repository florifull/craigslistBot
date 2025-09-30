"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";
import {
  X,
  MapPin,
  Clock,
  Zap,
  Settings,
  ExternalLink,
  CheckCircle,
} from "lucide-react";
import { createTask, CreateTaskRequest } from "@/lib/api";

interface CreateTaskModalProps {
  onClose: () => void;
  onTaskCreated?: () => void;
}

export function CreateTaskModal({
  onClose,
  onTaskCreated,
}: CreateTaskModalProps) {
  const { data: session } = useSession();
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    location: "",
    distance: 15,
    frequencyMinutes: 120,
    discordWebhookUrl: "",
    strictness: "strict" as "less_strict" | "strict" | "very_strict",
    enableInitialScrape: true,
    initialScrapeCount: 6,
  });

  const [isCreating, setIsCreating] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  const [creationResult, setCreationResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsCreating(true);
    setError(null);

    if (!session?.user?.id) {
      setError("User session not found. Please try logging in again.");
      setIsCreating(false);
      return;
    }

    try {
      const taskRequest: CreateTaskRequest = {
        name: formData.name,
        description: formData.description,
        location: formData.location,
        distance: formData.distance,
        frequencyMinutes: formData.frequencyMinutes,
        discordWebhookUrl: formData.discordWebhookUrl,
        strictness: formData.strictness,
        userId: session.user.id,
        enableInitialScrape: formData.enableInitialScrape,
        initialScrapeCount: formData.initialScrapeCount,
      };

      const result = await createTask(taskRequest);
      console.log("Task creation result:", result);

      if (result.success) {
        console.log("Setting creation result:", result);
        setCreationResult(result);
        // Call the callback to refresh the task list immediately
        if (onTaskCreated) {
          onTaskCreated();
        }
        // Close the modal immediately to return to tasks page
        onClose();
      } else {
        setError(result.message || "Failed to create task");
      }
    } catch (err) {
      setError("An unexpected error occurred. Please try again.");
      console.error("Task creation error:", err);
    } finally {
      setIsCreating(false);
    }
  };

  const strictnessOptions = [
    {
      value: "less_strict",
      label: "Less Strict (≥50%)",
      description: "More listings, broader matches",
    },
    {
      value: "strict",
      label: "Strict (≥70%)",
      description: "Moderate filtering",
    },
    {
      value: "very_strict",
      label: "Very Strict (≥85%)",
      description: "Only highest quality matches",
    },
  ];

  return (
    <>
      {/* Modal */}
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
        <div className="bg-dark-800 border border-white/20 rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
          <div className="p-6">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-2xl font-bold text-white">
                  Create Monitoring Task
                </h2>
                <p className="text-white/60 mt-1">
                  Set up automated Craigslist monitoring
                </p>
              </div>
              <button
                onClick={onClose}
                className="p-2 hover:bg-white/5 rounded-lg text-white/60 hover:text-white transition-colors"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Task Name */}
              <div>
                <label className="block text-sm font-medium text-white mb-2">
                  Task Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g., Road Bike 54cm"
                  className="input-field w-full"
                  value={formData.name}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                />
              </div>

              {/* Description */}
              <div>
                <label className="block text-sm font-medium text-white mb-2">
                  Item Description *
                </label>
                <textarea
                  required
                  rows={3}
                  placeholder="Describe what you're looking for in detail..."
                  className="input-field w-full resize-none"
                  value={formData.description}
                  onChange={(e) =>
                    setFormData({ ...formData, description: e.target.value })
                  }
                />
              </div>

              {/* Location & Distance */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-white mb-2">
                    ZIP Code *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="94105"
                    className="input-field w-full"
                    value={formData.location}
                    onChange={(e) =>
                      setFormData({ ...formData, location: e.target.value })
                    }
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-white mb-2">
                    Distance (miles) *
                  </label>
                  <select
                    value={formData.distance}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        distance: parseInt(e.target.value),
                      })
                    }
                    className="input-field w-full"
                  >
                    {[5, 10, 15, 25, 50].map((dist) => (
                      <option key={dist} value={dist}>
                        {dist} miles
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Frequency */}
              <div>
                <label className="block text-sm font-medium text-white mb-2">
                  Check Frequency
                </label>
                <div className="flex items-center gap-2">
                  <span className="text-white/60">Every</span>
                  <select
                    value={formData.frequencyMinutes}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        frequencyMinutes: parseInt(e.target.value),
                      })
                    }
                    className="input-field"
                  >
                    <option value={2}>2 minutes</option>
                    <option value={5}>5 minutes</option>
                    <option value={15}>15 minutes</option>
                    <option value={30}>30 minutes</option>
                    <option value={60}>1 hour</option>
                    <option value={120}>2 hours</option>
                    <option value={240}>4 hours</option>
                    <option value={480}>8 hours</option>
                    <option value={720}>12 hours</option>
                    <option value={1440}>24 hours</option>
                  </select>
                </div>
                <p className="text-xs text-white/50 mt-1">
                  Minimum frequency is 2 minutes for testing
                </p>
              </div>

              {/* Strictness */}
              <div>
                <label className="block text-sm font-medium text-white mb-2">
                  Matching Strictness
                </label>
                <div className="space-y-2">
                  {strictnessOptions.map((option) => (
                    <label
                      key={option.value}
                      className="flex items-start gap-3 p-3 bg-white/5 rounded-lg hover:bg-white/10 cursor-pointer"
                    >
                      <input
                        type="radio"
                        name="strictness"
                        value={option.value}
                        checked={formData.strictness === option.value}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            strictness: e.target.value as any,
                          })
                        }
                        className="mt-1"
                      />
                      <div>
                        <div className="text-sm font-medium text-white">
                          {option.label}
                        </div>
                        <div className="text-xs text-white/60">
                          {option.description}
                        </div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              {/* Discord Webhook */}
              <div>
                <label className="block text-sm font-medium text-white mb-2">
                  Discord Webhook URL *
                </label>
                <div className="relative">
                  <input
                    type="url"
                    required
                    placeholder="https://discord.com/api/webhooks/..."
                    className="input-field w-full pr-10"
                    value={formData.discordWebhookUrl}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        discordWebhookUrl: e.target.value,
                      })
                    }
                  />
                </div>
                <p className="text-xs text-white/50 mt-1">
                  Create a webhook in your Discord channel to receive
                  notifications
                </p>
              </div>

              {/* Initial Scrape Toggle */}
              <div>
                <label className="block text-sm font-medium text-white mb-2">
                  Initial Scrape
                </label>
                <div className="space-y-3">
                  <label className="flex items-center gap-3 p-3 bg-white/5 rounded-lg hover:bg-white/10 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData.enableInitialScrape}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          enableInitialScrape: e.target.checked,
                        })
                      }
                      className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500"
                    />
                    <div>
                      <div className="text-white font-medium">
                        Enable initial scrape
                      </div>
                      <div className="text-white/60 text-sm">
                        {formData.enableInitialScrape
                          ? `Scrape up to ${formData.initialScrapeCount} recent listings immediately`
                          : "Start monitoring from now - only new posts will be detected"}
                      </div>
                    </div>
                  </label>

                  {formData.enableInitialScrape && (
                    <div className="ml-7">
                      <label className="block text-sm text-white/80 mb-2">
                        Number of listings to scrape:
                      </label>
                      <select
                        value={formData.initialScrapeCount}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            initialScrapeCount: parseInt(e.target.value),
                          })
                        }
                        className="input-field"
                      >
                        <option value={1}>1 listing</option>
                        <option value={2}>2 listings</option>
                        <option value={6}>6 listings</option>
                        <option value={10}>10 listings</option>
                      </select>
                    </div>
                  )}
                </div>
              </div>

              {/* Error Message */}
              {error && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
                  <p className="text-red-400 text-sm">{error}</p>
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={onClose}
                  className="flex-1 px-6 py-3 bg-white/5 hover:bg-white/10 text-white rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isCreating}
                  className="flex-1 btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isCreating ? (
                    <div className="flex items-center justify-center gap-2">
                      <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin"></div>
                      Creating Task...
                    </div>
                  ) : (
                    "Create Task"
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>

      {/* Success Modal */}
      {console.log("showSuccess state:", showSuccess)}
      {showSuccess && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-60 flex items-center justify-center p-4">
          <div className="bg-dark-800 border border-white/20 rounded-2xl w-full max-w-lg">
            <div className="p-6 text-center">
              <div className="w-16 h-16 bg-green-500/20 rounded-2xl mx-auto mb-4 flex items-center justify-center">
                <CheckCircle className="w-8 h-8 text-green-400" />
              </div>
              <h3 className="text-2xl font-bold text-white mb-2">
                Task Created Successfully!
              </h3>
              <p className="text-white/60 mb-6">
                {formData.enableInitialScrape ? (
                  <>
                    {creationResult?.initialScrapingResults?.matchesFound > 0
                      ? `Sent ${creationResult.initialScrapingResults.matchesFound} recent matched listings to your Discord.`
                      : "No recent posts found matching your criteria."}{" "}
                    The initial scrape checked the {formData.initialScrapeCount}{" "}
                    most recent posts. Rescraping every{" "}
                    {formData.frequencyMinutes >= 60
                      ? `${Math.floor(formData.frequencyMinutes / 60)} hour${
                          Math.floor(formData.frequencyMinutes / 60) > 1
                            ? "s"
                            : ""
                        }`
                      : `${formData.frequencyMinutes} minute${
                          formData.frequencyMinutes > 1 ? "s" : ""
                        }`}
                    .
                  </>
                ) : (
                  <>
                    Task created successfully! Monitoring will start from now -
                    only new posts will be detected. Rescraping every{" "}
                    {formData.frequencyMinutes >= 60
                      ? `${Math.floor(formData.frequencyMinutes / 60)} hour${
                          Math.floor(formData.frequencyMinutes / 60) > 1
                            ? "s"
                            : ""
                        }`
                      : `${formData.frequencyMinutes} minute${
                          formData.frequencyMinutes > 1 ? "s" : ""
                        }`}
                    .
                  </>
                )}
              </p>

              {creationResult?.initialScrapingResults && (
                <div className="bg-white/5 rounded-lg p-4 mb-6 text-left">
                  <h4 className="font-semibold text-white mb-2">
                    Initial Scraping Results
                  </h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex items-center gap-2 text-white/80">
                      <Zap className="w-4 h-4 text-green-400" />
                      <span>
                        Found{" "}
                        {creationResult.initialScrapingResults.matchesFound}{" "}
                        matching listings!
                      </span>
                    </div>
                    <div className="text-white/60">
                      Total listings scanned:{" "}
                      {creationResult.initialScrapingResults.totalListings}
                    </div>
                    {creationResult.initialScrapingResults.sampleListings
                      ?.length > 0 && (
                      <div className="ml-6 space-y-1 text-white/60">
                        {creationResult.initialScrapingResults.sampleListings
                          .slice(0, 3)
                          .map((listing: any, index: number) => (
                            <div key={index}>
                              • {listing.title} - {listing.price} (
                              {Math.round(listing.matchScore * 100)}% match)
                            </div>
                          ))}
                      </div>
                    )}
                  </div>
                </div>
              )}

              <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4 mb-6">
                <p className="text-blue-400 text-sm">
                  📱 Check your Discord channel for the initial sample posts!
                </p>
                <p className="text-blue-300 text-xs mt-1">
                  The bot will now monitor every{" "}
                  {formData.frequencyMinutes >= 60
                    ? `${Math.floor(formData.frequencyMinutes / 60)} hour${
                        Math.floor(formData.frequencyMinutes / 60) > 1
                          ? "s"
                          : ""
                      }`
                    : `${formData.frequencyMinutes} minute${
                        formData.frequencyMinutes > 1 ? "s" : ""
                      }`}
                </p>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => {
                    setShowSuccess(false);
                    onClose();
                  }}
                  className="flex-1 px-6 py-3 bg-white/5 hover:bg-white/10 text-white rounded-lg transition-colors"
                >
                  Close
                </button>
                <button
                  onClick={() => {
                    setShowSuccess(false);
                    onClose();
                  }}
                  className="flex-1 btn-primary"
                >
                  View in Dashboard
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
