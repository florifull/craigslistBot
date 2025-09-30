"use client";

import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { LoginForm } from "@/components/LoginForm";
import { DiscordIcon } from "@/components/DiscordIcon";

export default function HomePage() {
  const { data: session, status } = useSession();
  const router = useRouter();

  // Debug logging
  console.log("HomePage - Status:", status, "Session:", session);

  useEffect(() => {
    if (status === "authenticated") {
      router.push("/dashboard");
    }
  }, [status, router]);

  // Add timeout to prevent infinite loading
  useEffect(() => {
    const timer = setTimeout(() => {
      if (status === "loading") {
        console.log("Session loading timeout - forcing unauthenticated state");
      }
    }, 5000); // 5 second timeout

    return () => clearTimeout(timer);
  }, [status]);

  // Show loading or redirect authenticated users
  if (status === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 bg-gradient-to-br from-primary-500 to-discord-blurple rounded-2xl mx-auto mb-4 flex items-center justify-center">
            <div className="w-6 h-6 border-2 border-white/20 border-t-white rounded-full animate-spin"></div>
          </div>
          <p className="text-white/60">Loading...</p>
        </div>
      </div>
    );
  }

  if (status === "authenticated") {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 bg-gradient-to-br from-primary-500 to-discord-blurple rounded-2xl mx-auto mb-4 flex items-center justify-center">
            <div className="w-6 h-6 border-2 border-white/20 border-t-white rounded-full animate-spin"></div>
          </div>
          <p className="text-white/60">Redirecting to dashboard...</p>
        </div>
      </div>
    );
  }
  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      {/* Background decoration */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-primary-500/10 rounded-full blur-3xl"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-discord-blurple/10 rounded-full blur-3xl"></div>
      </div>

      <div className="relative w-full max-w-md">
        {/* Main card */}
        <div className="card">
          <div className="text-center mb-8">
            <div className="w-16 h-16 bg-gradient-to-br from-primary-500 to-discord-blurple rounded-2xl mx-auto mb-4 flex items-center justify-center">
              <span className="text-2xl">🤖</span>
            </div>
            <h1 className="text-3xl font-bold gradient-text mb-2">
              Craigslist Bot
            </h1>
            <p className="text-white/70">
              Intelligent monitoring for your dream finds
            </p>
          </div>

          <LoginForm />
        </div>

        {/* Features preview */}
        <div className="mt-8 space-y-4">
          <div className="text-center">
            <h2 className="text-lg font-semibold text-white mb-4">
              Why Craigslist Bot?
            </h2>
          </div>

          <div className="grid grid-cols-1 gap-3">
            <div className="flex items-center gap-3 text-white/80">
              <div className="w-8 h-8 bg-primary-500/20 rounded-lg flex items-center justify-center">
                <span className="text-sm">🧠</span>
              </div>
              <span className="text-sm">AI-powered filtering</span>
            </div>

            <div className="flex items-center gap-3 text-white/80">
              <div className="w-8 h-8 bg-discord-blurple/20 rounded-lg flex items-center justify-center">
                <span className="text-sm">⚡</span>
              </div>
              <span className="text-sm">Real-time Discord notifications</span>
            </div>

            <div className="flex items-center gap-3 text-white/80">
              <div className="w-8 h-8 bg-primary-500/20 rounded-lg flex items-center justify-center">
                <span className="text-sm">🎯</span>
              </div>
              <span className="text-sm">Smart duplicate detection</span>
            </div>

            <div className="flex items-center gap-3 text-white/80">
              <div className="w-8 h-8 bg-discord-blurple/20 rounded-lg flex items-center justify-center">
                <span className="text-sm">⏰</span>
              </div>
              <span className="text-sm">Customizable monitoring frequency</span>
            </div>
          </div>
        </div>

        <div className="mt-8 text-center text-xs text-white/50">
          By continuing, you agree to our Terms of Service and Privacy Policy
        </div>
      </div>
    </div>
  );
}
