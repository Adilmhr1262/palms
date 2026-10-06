"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import SiteHeader from "@/components/SiteHeader";
import { getMe, type Me, type UserRole } from "@/lib/api";

export default function RoleLayout({
  allowed,
  nav,
  children,
}: {
  allowed: UserRole[];
  nav: { label: string; href: string }[];
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [me, setMe] = useState<Me | null>(null);

  useEffect(() => {
    getMe()
      .then((u) => {
        if (!allowed.includes(u.role)) router.replace("/login");
        else setMe(u);
      })
      .catch(() => router.replace("/login"));
  }, [router, allowed]);

  if (!me) return null;
  return (
    <>
      <SiteHeader
        nav={nav.map((n) => ({
          ...n,
          active: pathname === n.href || pathname.startsWith(n.href + "/"),
        }))}
        userName={me.full_name}
        userRole={me.role}
      />
      <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
    </>
  );
}
