import { Link } from "react-router-dom";

import { DilutionCalculator } from "../components/DilutionCalculator";
import { Button } from "../components/ui/Button";

export default function CalculatorPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center px-6 py-16">
      <h1 className="mb-1 text-3xl font-semibold">What's your number?</h1>
      <p className="mb-8 text-white/60">
        Play with the numbers. How big a yacht do you want — and how much of the company will you
        still own to buy it?
      </p>

      <div className="mb-6">
        <DilutionCalculator />
      </div>

      <div className="flex flex-col gap-3 sm:flex-row">
        <Link to="/critique" className="flex-1">
          <Button variant="secondary" className="w-full">
            Back to critique
          </Button>
        </Link>
        <Link to="/roadmap" className="flex-1">
          <Button className="w-full">See the founder roadmap</Button>
        </Link>
      </div>
    </main>
  );
}
