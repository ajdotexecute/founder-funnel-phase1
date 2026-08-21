import { useState } from "react";

import { Button } from "./ui/Button";
import { Card } from "./ui/Card";
import { Input } from "./ui/Input";

const MAX_ATTEMPTS = 3;

type StageBand = "Seed" | "Series A" | "Series B" | "Series C";

function detectStageBand(raiseGbp: number): StageBand {
  if (raiseGbp < 1_000_000) return "Seed";
  if (raiseGbp < 20_000_000) return "Series A";
  if (raiseGbp < 50_000_000) return "Series B";
  return "Series C";
}

function formatGbp(n: number): string {
  return new Intl.NumberFormat("en-GB", {
    style: "currency",
    currency: "GBP",
    maximumFractionDigits: 0,
  }).format(n);
}

interface Result {
  dilutionPct: number;
  ownershipPct: number;
  stageBand: StageBand;
}

export function DilutionCalculator() {
  const [valuation, setValuation] = useState("4000000");
  const [raise, setRaise] = useState("500000");
  const [result, setResult] = useState<Result | null>(null);
  const [attempts, setAttempts] = useState(0);

  const gated = attempts >= MAX_ATTEMPTS;
  const valuationNum = Number(valuation) || 0;
  const raiseNum = Number(raise) || 0;

  function reveal() {
    if (gated || valuationNum <= 0 || raiseNum < 0) return;

    const dilutionPct = (raiseNum / (valuationNum + raiseNum)) * 100;
    setResult({
      dilutionPct,
      ownershipPct: 100 - dilutionPct,
      stageBand: detectStageBand(raiseNum),
    });
    setAttempts((a) => a + 1);
  }

  return (
    <Card>
      <div className="mb-6 grid grid-cols-1 gap-5 sm:grid-cols-2">
        <div>
          <label className="mb-1.5 block text-sm text-white/70">Pre-money valuation</label>
          <Input
            type="number"
            min={0}
            value={valuation}
            onChange={(e) => setValuation(e.target.value)}
            disabled={gated}
          />
        </div>
        <div>
          <label className="mb-1.5 block text-sm text-white/70">Raise amount</label>
          <Input
            type="number"
            min={0}
            value={raise}
            onChange={(e) => setRaise(e.target.value)}
            disabled={gated}
          />
        </div>
      </div>

      {!gated && (
        <Button onClick={reveal} className="mb-6 w-full">
          What's my number?
        </Button>
      )}

      {gated && (
        <Card className="mb-6 border-steel/40 bg-steel/10">
          <p className="font-medium">You've used all {MAX_ATTEMPTS} goes for this session.</p>
          <p className="mt-1 text-white/70">
            Want to talk through what this actually means for your raise? Talk to us.
          </p>
        </Card>
      )}

      {result && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Stat label="Dilution" value={`${result.dilutionPct.toFixed(1)}%`} />
          <Stat label="Your ownership after" value={`${result.ownershipPct.toFixed(1)}%`} />
          <Stat label="Stage band" value={result.stageBand} />
        </div>
      )}

      <p className="mt-6 text-xs text-white/40">
        {formatGbp(valuationNum)} valuation + {formatGbp(raiseNum)} raise · attempt{" "}
        {Math.min(attempts + (gated ? 0 : 1), MAX_ATTEMPTS)} of {MAX_ATTEMPTS}
      </p>
    </Card>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-black/30 p-4 text-center">
      <div className="text-xs uppercase tracking-wide text-white/40">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-steel">{value}</div>
    </div>
  );
}
