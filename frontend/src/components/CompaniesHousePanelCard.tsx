import type { CompaniesHousePanel } from "../lib/api";
import { Card } from "./ui/Card";

export function CompaniesHousePanelCard({ panel }: { panel: CompaniesHousePanel }) {
  return (
    <Card className="mb-8">
      <h2 className="mb-3 text-sm uppercase tracking-wide text-white/40">Companies House</h2>

      {panel.status === "verified" ? (
        <div>
          <span className="mb-3 inline-block rounded-full border border-green-500 px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide text-green-400">
            ✓ Verified with Companies House
          </span>
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <dt className="text-xs uppercase tracking-wide text-white/40">Company name</dt>
              <dd className="mt-0.5">{panel.company_name ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-white/40">Status</dt>
              <dd className="mt-0.5">{panel.company_status ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-white/40">Incorporated</dt>
              <dd className="mt-0.5">{panel.incorporation_date ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-white/40">SIC codes</dt>
              <dd className="mt-0.5">{panel.sic_codes.length ? panel.sic_codes.join(", ") : "—"}</dd>
            </div>
          </dl>
        </div>
      ) : (
        <p className="text-sm italic text-white/40">Not checked</p>
      )}
    </Card>
  );
}
