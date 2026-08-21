import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import { createSubmission } from "../lib/api";

export default function UploadPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [deck, setDeck] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (!email.includes("@")) {
      setError("Enter a valid email address.");
      return;
    }

    setSubmitting(true);
    try {
      const submission = await createSubmission(email, companyName, deck);
      navigate("/critique", { state: { submission } });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-xl flex-col justify-center px-6 py-16">
      <h1 className="mb-2 text-3xl font-semibold">Founder Funnel</h1>
      <p className="mb-8 text-white/60">
        Upload your pitch deck. We'll pull out the basics and show you where the gaps are.
      </p>

      <Card>
        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          <div>
            <label className="mb-1.5 block text-sm text-white/70">
              Email <span className="text-steel">*</span>
            </label>
            <Input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
            />
          </div>

          <div>
            <label className="mb-1.5 block text-sm text-white/70">Company name (optional)</label>
            <Input
              type="text"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              placeholder="Acme Robotics"
            />
          </div>

          <div>
            <label className="mb-1.5 block text-sm text-white/70">Pitch deck (optional, PDF)</label>
            <input
              type="file"
              accept="application/pdf"
              onChange={(e) => setDeck(e.target.files?.[0] ?? null)}
              className="block w-full text-sm text-white/70 file:mr-4 file:rounded-lg file:border-0 file:bg-steel file:px-4 file:py-2 file:text-white file:cursor-pointer"
            />
          </div>

          {error && <p className="text-sm text-red-400">{error}</p>}

          <Button type="submit" disabled={submitting}>
            {submitting ? "Uploading…" : "See my deck critique"}
          </Button>
        </form>
      </Card>
    </main>
  );
}
