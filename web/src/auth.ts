import NextAuth, { CredentialsSignin } from "next-auth";
import Credentials from "next-auth/providers/credentials";
import Google from "next-auth/providers/google";
import { MongoDBAdapter } from "@auth/mongodb-adapter";
import { getMongoClient, getUsersCollection } from "@/lib/db";
import { verifyPassword } from "@/lib/password";
import { clientIp, consume, LIMITS, reset } from "@/lib/rate-limit";
import { signInSchema } from "@/lib/validation";

/** Same error for unknown usernames and wrong passwords, so login never reveals which accounts exist. */
class InvalidCredentials extends CredentialsSignin {
  code = "invalid_credentials";
}

class TooManyAttempts extends CredentialsSignin {
  code = "rate_limited";
}

const DAY_SECONDS = 24 * 60 * 60;

/** Pages that need a signed-in user. The proxy redirects; each page also checks for itself. */
export const PROTECTED_PATHS = ["/quests", "/friends", "/profile"];

export function isProtectedPath(pathname: string) {
  return PROTECTED_PATHS.some((path) => pathname === path || pathname.startsWith(`${path}/`));
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  adapter: MongoDBAdapter(getMongoClient),
  // The Credentials provider only works with JWT sessions: an encrypted, httpOnly cookie
  // (Secure and __Secure- prefixed on HTTPS). Users and Google accounts still live in MongoDB.
  session: { strategy: "jwt", maxAge: 30 * DAY_SECONDS, updateAge: DAY_SECONDS },
  pages: { signIn: "/sign-in", error: "/sign-in" },
  providers: [
    // Reads AUTH_GOOGLE_ID / AUTH_GOOGLE_SECRET. allowDangerousEmailAccountLinking stays off:
    // a Google sign-in whose email belongs to a password account fails with OAuthAccountNotLinked.
    Google,
    Credentials({
      credentials: {
        username: { label: "Username" },
        password: { label: "Password", type: "password" },
      },
      async authorize(rawCredentials, request) {
        const parsed = signInSchema.safeParse(rawCredentials);
        if (!parsed.success) throw new InvalidCredentials();
        const { username, password } = parsed.data;

        const ip = clientIp(request.headers);
        const accountKey = `sign-in:${ip}:${username}`;
        if (!consume(`sign-in:${ip}`, LIMITS.signInPerIp) || !consume(accountKey, LIMITS.signInPerAccount)) {
          throw new TooManyAttempts();
        }

        const users = await getUsersCollection();
        const user = await users.findOne(
          { username },
          { projection: { username: 1, name: 1, email: 1, image: 1, passwordHash: 1 } },
        );
        // Always runs a hash comparison, even for unknown usernames.
        const valid = await verifyPassword(user?.passwordHash, password);
        if (!user || !valid) throw new InvalidCredentials();

        reset(accountKey);
        return {
          id: user._id.toHexString(),
          name: user.name ?? user.username,
          email: user.email,
          image: user.image,
          username: user.username,
        };
      },
    }),
  ],
  callbacks: {
    authorized({ auth, request }) {
      return isProtectedPath(request.nextUrl.pathname) ? Boolean(auth?.user) : true;
    },
    signIn({ account, profile }) {
      // Only accept Google identities whose email Google has verified.
      if (account?.provider === "google") return profile?.email_verified === true;
      return true;
    },
    jwt({ token, user }) {
      // `user` is only present at sign-in. Copy the id and username only; never the password hash.
      if (user) {
        token.uid = user.id;
        token.username = user.username ?? null;
      }
      return token;
    },
    session({ session, token }) {
      if (token.uid) session.user.id = token.uid;
      session.user.username = token.username ?? null;
      return session;
    },
  },
});
