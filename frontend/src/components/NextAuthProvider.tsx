"use client";

import { SessionProvider } from "next-auth/react";

interface NextAuthProviderProps {
  children: React.ReactNode;
}

export function NextAuthProvider({ children }: NextAuthProviderProps) {
  return (
    <SessionProvider
      refetchInterval={5 * 60} // Refetch session every 5 minutes instead of default 30 seconds
      refetchOnWindowFocus={false} // Don't refetch when window gains focus
    >
      {children}
    </SessionProvider>
  );
}
