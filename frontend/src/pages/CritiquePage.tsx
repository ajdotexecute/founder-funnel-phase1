import { Link, Navigate, useLocation } from "react-router-dom";

import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import type { Submission } from "../lib/api";

export default function CritiquePage() {
  const location = useLocation();
  const submission = (location.state as { submission?: Submission } | null)?.submission;

  if (!submission) {
    return <Navigate to="/" replace />;
  }

  const facts = [
    { label: "Company", value: submission.company_name ?? "Not detected" },
    { label: "Sector", value: submission.sector },
    { label: "Industry", value: submission.industry },
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
        <Link to="/roadmap" className="flex-1">
          <Button variant="secondary" className="w-full">
            See the founder roadmap
          </Button>
        </Link>
        <Link to="/calculator" className="flex-1">
          <Button className="w-full">What's your number?</Button>
        </Link>
      </div>
    </main>
  );
}
