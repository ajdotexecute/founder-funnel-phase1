import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { getSubmission, type Submission } from "../lib/api";

type LoadState = "loading" | "not-found" | "error" | "ready";

export default function CritiquePage() {
  const { id } = useParams<{ id: string }>();
  const [submission, setSubmission] = useState<Submission | null>(null);
  const [state, setState] = useState<LoadState>("loading");

  useEffect(() => {
    if (!id) {
      setState("not-found");
      return;
    }
    setState("loading");
    getSubmission(id)
      .then((result) => {
        if (result) {
          setSubmission(result);
          setState("ready");
        } else {
          setState("not-found");
        }
      })
      .catch(() => setState("error"));
  }, [id]);

  if (state === "loading") {
    return (
      <main className="mx-auto flex min-h-screen max-w-2xl flex-col items-center justify-center px-6 py-16">
        <p className="text-white/60">Loading…</p>
      </main>
    );
  }

  if (state === "not-found") {
    return (
      <main className="mx-auto flex min-h-screen max-w-xl flex-col items-center justify-center px-6 py-16 text-center">
        <h1 className="mb-2 text-2xl font-semibold">We couldn't find that submission</h1>
        <p className="mb-8 text-white/60">
          The link may be wrong, or the submission may no longer exist.
        </p>
        <Link to="/">
          <Button>Start a new upload</Button>
        </Link>
      </main>
    );
  }

  if (state === "error" || !submission) {
    return (
      <main className="mx-auto flex min-h-screen max-w-xl flex-col items-center justify-center px-6 py-16 text-center">
        <h1 className="mb-2 text-2xl font-semibold">Something went wrong</h1>
        <p className="mb-8 text-white/60">Please try again in a moment.</p>
        <Link to="/">
          <Button>Start a new upload</Button>
        </Link>
      </main>
    );
  }

  const facts = [
    { label: "Company", value: submission.company_name ?? "Not detected" },
    { label: "Sector", value: submission.extracted_sector },
    { label: "Industry", value: submission.extracted_industry },
    { label: "Raise amount", value: submission.raise_amount },
  ];

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center px-6 py-16">
      <h1 className="mb-1 text-3xl font-semibold">Here's what we read from your deck</h1>
      <p className="mb-8 text-white/60">A statement of facts, not a judgement.</p>

      <Card className="mb-6">
        <dl className="grid grid-cols-2 gap-4">
          {facts.map((fact) => (
            <div key={fact.label}>
              <dt className="text-xs uppercase tracking-wide text-white/40">{fact.label}</dt>
              <dd className="mt-1 text-lg">{fact.value}</dd>
            </div>
          ))}
        </dl>
      </Card>

      <Card className="mb-8">
        <h2 className="mb-3 text-sm uppercase tracking-wide text-white/40">
          Questions you need to consider
        </h2>
        <ul className="flex flex-col gap-2">
          {submission.gap_flags.map((flag) => (
            <li key={flag} className="flex gap-2 text-white/80">
              <span className="text-steel">–</span>
              <span>{flag}</span>
            </li>
          ))}
        </ul>
      </Card>

      <div className="flex flex-col gap-3 sm:flex-row">
        <Link to={`/roadmap/${submission.id}`} className="flex-1">
          <Button variant="secondary" className="w-full">
            See the founder roadmap
          </Button>
        </Link>
        <Link to={`/calculator/${submission.id}`} className="flex-1">
          <Button className="w-full">What's your number?</Button>
        </Link>
      </div>
    </main>
  );
}
