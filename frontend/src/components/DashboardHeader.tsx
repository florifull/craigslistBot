"use client";

import { useState } from "react";
import { useSession, signOut } from "next-auth/react";
import { User, Bell, Settings, LogOut } from "lucide-react";

export function DashboardHeader() {
  const [showUserMenu, setShowUserMenu] = useState(false);
  const { data: session } = useSession();

  const handleSignOut = () => {
    signOut({ callbackUrl: "/" });
  };

  // Use session data or fallback to mock data for development
  const user = session?.user || {
    name: "Alex Sky",
    email: "alexskyhworking@gmail.com",
    image: "https://cdn.discordapp.com/embed/avatars/0.png",
  };

  return (
    <header className="bg-white/5 backdrop-blur-sm border-b border-white/10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-gradient-to-br from-primary-500 to-discord-blurple rounded-lg flex items-center justify-center">
              <span className="text-sm">🤖</span>
            </div>
            <h1 className="text-xl font-bold gradient-text">Craigslist Bot</h1>
          </div>

          {/* Right side */}
          <div className="flex items-center gap-4">
            {/* Notifications */}
            <button className="p-2 text-white/60 hover:text-white transition-colors">
              <Bell className="w-5 h-5" />
            </button>

            {/* User menu */}
            <div className="relative">
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="flex items-center gap-3 p-2 hover:bg-white/5 rounded-lg transition-colors"
              >
                <img
                  src={user.image || (user as any).avatar}
                  alt={user.name}
                  className="w-8 h-8 rounded-full"
                />
                <div className="text-left">
                  <div className="text-sm font-medium text-white">
                    {user.name}
                  </div>
                  <div className="text-xs text-white/60">{user.email}</div>
                </div>
                <User className="w-4 h-4 text-white/60" />
              </button>

              {/* Dropdown menu */}
              {showUserMenu && (
                <div className="absolute right-0 mt-2 w-48 bg-white/10 backdrop-blur-sm border border-white/20 rounded-lg shadow-xl py-1">
                  <button className="flex items-center gap-2 px-4 py-2 text-sm text-white hover:bg-white/5 w-full">
                    <User className="w-4 h-4" />
                    Profile
                  </button>
                  <button className="flex items-center gap-2 px-4 py-2 text-sm text-white hover:bg-white/5 w-full">
                    <Settings className="w-4 h-4" />
                    Settings
                  </button>
                  <div className="border-t border-white/10 my-1"></div>
                  <button
                    onClick={handleSignOut}
                    className="flex items-center gap-2 px-4 py-2 text-sm text-red-400 hover:bg-red-500/10 w-full"
                  >
                    <LogOut className="w-4 h-4" />
                    Sign Out
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
