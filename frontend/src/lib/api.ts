export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface DocumentSummary {
  slot: "deck" | "forecast" | "one_pager";
  filename: string;
  size: number;
  mime_type: string;
}

export interface MarketSizeClaim {
  claim: string;
  stated_basis: string;
}

export interface ExtractionSummary {
  company: string | null;
  extracted_sector: string | null;
  stage: string | null;
  ask_amount: string | null;
  use_of_funds: string | null;
  traction_metrics: string[];
  team: string[];
  market_size_claims: MarketSizeClaim[];
  revenue_model: string | null;
  key_risks: string[];
  companies_house: Record<string, unknown> | null;
}

export interface DimensionScoreSummary {
  id: string;
  name: string;
  score: number;
  label: string;
  rag: "red" | "amber" | "green";
  evidence: string;
  feedback: string[];
}

export interface ScoreSummary {
  overall_score: number;
  config_id: string;
  config_version: string;
  dimensions: DimensionScoreSummary[];
}

export interface Submission {
  id: string;
  email: string;
  version: number;
  company_name: string | null;
  declared_sector: string | null;
  companies_house_number: string | null;
  notes: string | null;
  consent_at: string | null;
  created_at: string;
  documents: DocumentSummary[];
  extraction: ExtractionSummary | null;
  score: ScoreSummary | null;
  report_url: string | null;
  processing_error: string | null;
}

export interface FieldErrors {
  [field: string]: string;
}

export class ValidationError extends Error {
  errors: FieldErrors;
  constructor(errors: FieldErrors) {
    super("Validation failed.");
    this.errors = errors;
  }
}

export async function getSectors(): Promise<string[]> {
  const res = await fetch(`${API_URL}/api/config/sectors`);
  if (!res.ok) throw new Error("Could not load sector list.");
  return res.json();
}

export interface CreateSubmissionInput {
  email: string;
  companyName: string;
  declaredSector: string;
  companiesHouseNumber: string;
  notes: string;
  consent: boolean;
  deck: File | null;
  forecast: File | null;
  onePager: File | null;
}

export async function createSubmission(input: CreateSubmissionInput): Promise<Submission> {
  const form = new FormData();
  form.append("email", input.email);
  if (input.companyName) form.append("company_name", input.companyName);
  if (input.declaredSector) form.append("declared_sector", input.declaredSector);
  if (input.companiesHouseNumber) form.append("companies_house_number", input.companiesHouseNumber);
  if (input.notes) form.append("notes", input.notes);
  form.append("consent", input.consent ? "true" : "false");
  if (input.deck) form.append("deck", input.deck);
  if (input.forecast) form.append("forecast", input.forecast);
  if (input.onePager) form.append("one_pager", input.onePager);

  const res = await fetch(`${API_URL}/api/submissions`, { method: "POST", body: form });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    if (res.status === 400 && body?.detail?.errors) {
      throw new ValidationError(body.detail.errors);
    }
    throw new Error(body?.detail ?? "Submission failed.");
  }

  return res.json();
}

export async function getSubmission(id: string): Promise<Submission | null> {
  const res = await fetch(`${API_URL}/api/submissions/${id}`);
  if (res.status === 404 || res.status === 422) return null;
  if (!res.ok) throw new Error("Could not load submission.");
  return res.json();
}
