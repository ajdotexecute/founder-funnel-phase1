import { Link } from "react-router-dom";

import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";

const STAGES = [
  { name: "Pre-seed", description: "Idea, founding team, and early proof of concept." },
  { name: "Seed", description: "Product in market, early traction, first outside capital." },
  { name: "Series A", description: "Repeatable growth engine, scaling the team." },
  { name: "Series B+", description: "Proven model, scaling into new markets." },
];

export default function RoadmapPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center px-6 py-16">
      <h1 className="mb-1 text-3xl font-semibold">The founder roadmap</h1>
      <p className="mb-8 text-white/60">
        A general guide to the funding journey. Not personalised to your numbers.
      </p>

      <div className="mb-8 flex flex-col gap-4">
        {STAGES.map((stage) => (
          <Card key={stage.name}>
            <h2 className="mb-1 text-lg font-medium text-steel">{stage.name}</h2>
            <p className="text-white/70">{stage.description}</p>
          </Card>
        ))}
      </div>

      <div className="flex flex-col gap-3 sm:flex-row">
        <Link to="/" className="flex-1">
          <Button variant="secondary" className="w-full">
            Back to start
          </Button>
        </Link>
        <Link to="/calculator" className="flex-1">
          <Button className="w-full">What's your number?</Button>
        </Link>
      </div>
    </main>
  );
}
