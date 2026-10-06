import SiteHeader from "@/components/SiteHeader";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <SiteHeader nav={[{ label: "Users", href: "/admin/users", active: true }]} />
      <main className="mx-auto max-w-5xl px-6 py-8">{children}</main>
    </>
  );
}
