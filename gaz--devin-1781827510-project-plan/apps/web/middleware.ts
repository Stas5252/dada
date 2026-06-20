import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const token = request.cookies.get("cf_access_token")?.value;

  // Protect these routes
  const protectedRoutes = [
    "/dashboard",
    "/onboarding",
    "/agents",
    "/knowledge",
    "/test-console",
    "/conversations",
    "/analytics",
    "/settings",
  ];

  const isProtected = protectedRoutes.some((route) => request.nextUrl.pathname.startsWith(route));

  if (isProtected && !token) {
    const loginUrl = new URL("/login", request.url);
    return NextResponse.redirect(loginUrl);
  }

  // Redirect from entry auth pages if already logged in. Token-based pages must stay reachable.
  const authRoutes = ["/login", "/register", "/forgot-password"];
  const isAuthRoute = authRoutes.some((route) => request.nextUrl.pathname.startsWith(route));

  if (isAuthRoute && token) {
    const dashboardUrl = new URL("/dashboard", request.url);
    return NextResponse.redirect(dashboardUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!api|_next/static|_next/image|favicon.ico).*)",
  ],
};
