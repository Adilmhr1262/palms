type SiteHeaderProps = {
  nav?: { label: string; href: string; active?: boolean }[];
  userName?: string;
  userRole?: string;
};

export default function SiteHeader({ nav = [], userName, userRole }: SiteHeaderProps) {
  return (
    <header className="border-b border-line bg-paper">
      <div className="mx-auto flex max-w-6xl items-center gap-8 px-6 py-3">
        <div className="whitespace-nowrap">
          <div className="text-base font-semibold tracking-wide text-ink">PALMS</div>
          <div className="text-[11px] tracking-wide text-muted">
            Personalized Adaptive Learning Management System
          </div>
        </div>
        {nav.length > 0 && (
          <nav className="flex gap-5">
            {nav.map((item) => (
              <a
                key={item.href}
                href={item.href}
                className={
                  item.active
                    ? "border-b-2 border-ink pb-1 font-semibold text-ink no-underline"
                    : "pb-1 text-ink no-underline"
                }
              >
                {item.label}
              </a>
            ))}
          </nav>
        )}
        <div className="ml-auto text-right text-[13px] text-muted">
          {userName ? (
            <>
              <div className="font-semibold text-ink">{userName}</div>
              <div>{userRole}</div>
            </>
          ) : (
            <a href="/login" className="no-underline">
              Sign in
            </a>
          )}
        </div>
      </div>
    </header>
  );
}
