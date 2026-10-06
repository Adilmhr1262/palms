import { NextRequest, NextResponse } from "next/server";
import { COOKIE_NAME } from "@/lib/auth-cookie";

const BACKEND = process.env.BACKEND_URL || "http://localhost:8000";

export async function GET(req: NextRequest) {
  const token = req.cookies.get(COOKIE_NAME)?.value;
  if (!token) {
    return NextResponse.json({ detail: "Not authenticated." }, { status: 401 });
  }
  const res = await fetch(`${BACKEND}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
