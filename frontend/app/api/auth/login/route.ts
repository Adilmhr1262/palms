import { NextRequest, NextResponse } from "next/server";
import { COOKIE_NAME } from "@/lib/auth-cookie";

const BACKEND = process.env.BACKEND_URL || "http://localhost:8000";

function redirectFor(role: string): string {
  if (role === "admin") return "/admin/users";
  return "/";
}

export async function POST(req: NextRequest) {
  const body = await req.json();
  const res = await fetch(`${BACKEND}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) {
    return NextResponse.json(data, { status: res.status });
  }
  const response = NextResponse.json({
    user: data.user,
    redirect: redirectFor(data.user.role),
  });
  response.cookies.set(COOKIE_NAME, data.access_token, {
    httpOnly: true,
    path: "/",
    sameSite: "lax",
    secure: process.env.COOKIE_SECURE === "true",
    // Matches the backend access-token lifetime (2 hours).
    maxAge: 60 * 60 * 2,
  });
  return response;
}
