// Redirects signed-out visitors from protected pages to /sign-in (see `authorized` in auth.ts).
// Pages and server actions still check the session themselves; this is the first line only.
export { auth as proxy } from "@/auth";

export const config = {
  matcher: ["/quests/:path*", "/friends/:path*", "/profile/:path*", "/settings/:path*"],
};
