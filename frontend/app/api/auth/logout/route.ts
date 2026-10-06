import { NextResponse } from "next/server";
import { COOKIE_NAME } from "@/lib/auth-cookie";

export async function POST() {
  const response = NextResponse.json({ status: "logged out" });
  response.cookies.set(COOKIE_NAME, "", {
    httpOnly: true,
    path: "/",
    maxAge: 0,
  });
  return response;
}
