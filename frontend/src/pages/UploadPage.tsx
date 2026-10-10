import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { FileInput } from "../components/ui/FileInput";
import { Input } from "../components/ui/Input";
import { Select } from "../components/ui/Select";
import { Textarea } from "../components/ui/Textarea";
import { createSubmission, getSectors, ValidationError, type FieldErrors } from "../lib/api";

const ACCEPTED_TYPES = ".pdf,.pptx,.xlsx,.csv,.docx";

function FieldError({ message }: { message?: string }) {
  if (!message) return null;
  return <p className="mt-1 text-sm text-red-400">{message}</p>;
}

export default function UploadPage() {
  const navigate = useNavigate();
  const [sectors, setSectors] = useState<string[]>([]);

  const [email, setEmail] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [declaredSector, setDeclaredSector] = useState("");
  const [companiesHouseNumber, setCompaniesHouseNumber] = useState("");
  const [notes, setNotes] = useState("");
  const [consent, setConsent] = useState(false);
  const [deck, setDeck] = useState<File | null>(null);
  const [forecast, setForecast] = useState<File | null>(null);
  const [onePager, setOnePager] = useState<File | null>(null);

  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    getSectors()
      .then(setSectors)
      .catch(() => setSectors([]));
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    setFieldErrors({});

    setSubmitting(true);
    try {
      const submission = await createSubmission({
        email,
        companyName,
        declaredSector,
        companiesHouseNumber,
        notes,
        consent,
        deck,
        forecast,
        onePager,
      });
      navigate(`/critique/${submission.id}`);
    } catch (err) {
      if (err instanceof ValidationError) {
        setFieldErrors(err.errors);
      } else {
        setFormError(err instanceof Error ? err.message : "Something went wrong.");
      }
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
            <FieldError message={fieldErrors.email} />
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
            <label className="mb-1.5 block text-sm text-white/70">Sector (optional)</label>
            <Select value={declaredSector} onChange={(e) => setDeclaredSector(e.target.value)}>
              <option value="">Select a sector…</option>
              {sectors.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </Select>
            <FieldError message={fieldErrors.declared_sector} />
          </div>

          <div>
            <label className="mb-1.5 block text-sm text-white/70">Companies House number (optional)</label>
            <Input
              type="text"
              value={companiesHouseNumber}
              onChange={(e) => setCompaniesHouseNumber(e.target.value)}
              placeholder="e.g. 01234567"
            />
            <FieldError message={fieldErrors.companies_house_number} />
          </div>

          <div>
            <label className="mb-1.5 block text-sm text-white/70">Notes (optional)</label>
            <Textarea
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Anything else worth knowing?"
            />
          </div>

          <div className="flex flex-col gap-4 border-t border-white/10 pt-5">
            <FileInput label="Pitch deck" required accept={ACCEPTED_TYPES} onChange={setDeck} />
            <FieldError message={fieldErrors.deck} />

            <FileInput label="Financial forecast" accept={ACCEPTED_TYPES} onChange={setForecast} />
            <FieldError message={fieldErrors.forecast} />

            <FileInput label="One-pager" accept={ACCEPTED_TYPES} onChange={setOnePager} />
            <FieldError message={fieldErrors.one_pager} />

            <p className="text-xs text-white/40">Accepted: PDF, PPTX, XLSX, CSV, DOCX. Up to 20MB each.</p>
          </div>

          <div className="border-t border-white/10 pt-5">
            <label className="flex items-start gap-2 text-sm text-white/70">
              <input
                type="checkbox"
                checked={consent}
                onChange={(e) => setConsent(e.target.checked)}
                className="mt-0.5"
              />
              <span>
                I agree to the{" "}
                <Link to="/terms" target="_blank" className="text-steel underline">
                  terms and privacy notice
                </Link>
                . <span className="text-steel">*</span>
              </span>
            </label>
            <FieldError message={fieldErrors.consent} />
          </div>

          {formError && <p className="text-sm text-red-400">{formError}</p>}

          <Button type="submit" disabled={submitting}>
            {submitting ? "Uploading…" : "See my deck critique"}
          </Button>
        </form>
      </Card>
    </main>
  );
}
