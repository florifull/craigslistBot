"use client";

import { useState } from "react";
import { signIn } from "next-auth/react";
import { useRouter } from "next/navigation";
import { DiscordIcon } from "./DiscordIcon";

export function LoginForm() {
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  const handleDiscordLogin = async () => {
    try {
      setIsLoading(true);
      const result = await signIn("discord", {
        redirect: false,
        callbackUrl: "/dashboard",
      });

      if (result?.ok) {
        router.push("/dashboard");
      } else if (result?.error) {
        console.error("Authentication failed:", result.error);
        alert(
          "Authentication failed. Please check your Discord app configuration."
        );
      }
    } catch (error) {
      console.error("Login error:", error);
      alert("An unexpected error occurred during authentication.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="text-center">
        <button
          onClick={handleDiscordLogin}
          disabled={isLoading}
          className="btn-discord w-full disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? (
            <div className="flex items-center gap-3">
              <div className="w-5 h-5 border-2 border-white/20 border-t-white rounded-full animate-spin"></div>
              <span>Connecting...</span>
            </div>
          ) : (
            <>
              <DiscordIcon />
              <span>Continue with Discord</span>
            </>
          )}
        </button>
      </div>

      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-white/10"></div>
        </div>
        <div className="relative flex justify-center text-sm">
          <span className="px-4 bg-dark-800 text-white/50">
            Secure authentication powered by Discord
          </span>
        </div>
      </div>

      <div className="text-center space-y-3">
        <div className="flex items-center justify-center gap-2 text-xs text-white/60">
          <span className="w-2 h-2 bg-green-400 rounded-full"></span>
          <span>All data is encrypted and secure</span>
        </div>
        <div className="flex items-center justify-center gap-2 text-xs text-white/60">
          <span className="w-2 h-2 bg-blue-400 rounded-full"></span>
          <span>Session valid for 7 days</span>
        </div>
      </div>
    </div>
  );
}
