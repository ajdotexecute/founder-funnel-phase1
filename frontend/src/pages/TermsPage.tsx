import { Card } from "../components/ui/Card";

export default function TermsPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center px-6 py-16">
      <h1 className="mb-1 text-3xl font-semibold">Terms &amp; privacy notice</h1>
      <p className="mb-8 text-white/60">Placeholder — real terms and privacy text aren't written yet.</p>

      <Card>
        <p className="text-white/70">
          This is a discovery prototype. This page is a placeholder so the consent checkbox on the
          upload form has somewhere real to link to. No binding terms or privacy policy exist yet —
          don't treat this as one.
        </p>
      </Card>
    </main>
  );
}
