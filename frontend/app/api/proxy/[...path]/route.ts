import { NextRequest, NextResponse } from "next/server";
import { COOKIE_NAME } from "@/lib/auth-cookie";

const BACKEND = process.env.BACKEND_URL || "http://localhost:8000";

async function handler(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const token = req.cookies.get(COOKIE_NAME)?.value;
  // All backend traffic, including resource downloads, goes through /api/v1
  // so the backend's authentication and authorization always apply.
  const target = `${BACKEND}/api/v1/${path.join("/")}${req.nextUrl.search}`;
  const hasBody = !["GET", "HEAD"].includes(req.method);
  const contentType = req.headers.get("content-type") || "";
  const headers: Record<string, string> = token
    ? { Authorization: `Bearer ${token}` }
    : {};
  let body: BodyInit | undefined;
  if (hasBody) {
    if (contentType.includes("multipart/form-data")) {
      // Pass the form through untouched; fetch sets the boundary itself.
      body = await req.formData();
    } else {
      headers["Content-Type"] = "application/json";
      body = await req.text();
    }
  }
  const res = await fetch(target, { method: req.method, headers, body });
  const buf = await res.arrayBuffer();
  return new NextResponse(buf, {
    status: res.status,
    headers: {
      "Content-Type": res.headers.get("content-type") || "application/json",
    },
  });
}

export {
  handler as DELETE,
  handler as GET,
  handler as PATCH,
  handler as POST,
  handler as PUT,
};
