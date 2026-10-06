import { NextRequest, NextResponse } from "next/server";
import { COOKIE_NAME } from "@/lib/auth-cookie";

// Cookie presence gates the app here. Roles are enforced by the backend
// on every request; that is the final security layer.
const PROTECTED = ["/admin", "/teacher", "/student"];

export function middleware(req: NextRequest) {
  const token = req.cookies.get(COOKIE_NAME)?.value;
  const { pathname } = req.nextUrl;
  if (PROTECTED.some((p) => pathname === p || pathname.startsWith(p + "/"))) {
    if (!token) {
      return NextResponse.redirect(new URL("/login", req.url));
    }
  }
  if (pathname === "/login" && token) {
    return NextResponse.redirect(new URL("/", req.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|api).*)"],
};
