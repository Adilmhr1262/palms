import SiteHeader from "@/components/SiteHeader";

export default function Home() {
  return (
    <>
      <SiteHeader />
      <main className="mx-auto max-w-3xl px-6 py-16">
        <h1 className="text-2xl font-semibold tracking-tight">
          Personalized Adaptive Learning Management System
        </h1>
        <p className="mt-4 text-muted">
          A mastery-based learning platform for education research. Teachers
          build courses and assessments, students follow personalized learning
          pathways, and every recommendation carries its reason.
        </p>
        <div className="mt-8">
          <a href="/login" className="btn-primary">
            Sign in
          </a>
        </div>
      </main>
    </>
  );
}
