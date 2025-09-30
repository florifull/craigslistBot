import NextAuth from "next-auth";
import DiscordProvider from "next-auth/providers/discord";

const handler = NextAuth({
  providers: [
    DiscordProvider({
      clientId: process.env.DISCORD_CLIENT_ID || "",
      clientSecret: process.env.DISCORD_CLIENT_SECRET || "",
      authorization: {
        params: {
          scope: "identify email",
        },
      },
    }),
  ],
  callbacks: {
    async jwt({ token, account, profile }) {
      // Persist the OAuth access_token and or the user id to the token right after signin
      if (account) {
        token.accessToken = account.access_token;
      }
      if (profile) {
        token.id = (profile as any).id;
        token.avatar = (profile as any).avatar;
        token.username = (profile as any).username;
        token.discriminator = (profile as any).discriminator;
      }
      return token;
    },
    async session({ session, token }) {
      // Send properties to the client, like an access_token and user id from a provider.
      if (session?.user && token) {
        session.user.id = token.id as string;
        session.user.image = `https://cdn.discordapp.com/avatars/${token.id}/${token.avatar}.png`;
        session.user.name = token.username as string;
        session.accessToken = token.accessToken;
      }
      return session;
    },
  },
  pages: {
    signIn: "/",
  },
  session: {
    maxAge: 7 * 24 * 60 * 60, // 7 days as requested
    strategy: "jwt" as const,
  },
  debug: process.env.NODE_ENV === "development",
});

export { handler as GET, handler as POST };
