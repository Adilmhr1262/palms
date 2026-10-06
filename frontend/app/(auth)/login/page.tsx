import LoginForm from "@/components/LoginForm";

export default function LoginPage() {
  return (
    <main className="min-h-screen bg-page">
      <div className="mx-auto max-w-sm px-6 pt-20">
        <div>
          <div className="text-base font-semibold tracking-wide text-ink">
            PALMS
          </div>
          <p className="mt-0.5 text-xs text-muted">
            Personalized Adaptive Learning Management System
          </p>
        </div>
        <div className="mt-6 rounded border border-line bg-paper p-6">
          <h1 className="text-lg font-semibold">Sign in</h1>
          <p className="mb-5 mt-1 text-sm text-muted">
            Use your PALMS account to continue.
          </p>
          <LoginForm />
        </div>
      </div>
    </main>
  );
}
