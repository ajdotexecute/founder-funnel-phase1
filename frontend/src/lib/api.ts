const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface Submission {
  id: string;
  email: string;
  company_name: string | null;
  deck_filename: string | null;
  sector: string | null;
  industry: string | null;
  raise_amount: string | null;
  gap_flags: string[];
  raising_raw: string | null;
  created_at: string;
}

export async function createSubmission(
  email: string,
  companyName: string,
  deck: File | null,
): Promise<Submission> {
  const form = new FormData();
  form.append("email", email);
  if (companyName) form.append("company_name", companyName);
  if (deck) form.append("deck", deck);

  const res = await fetch(`${API_URL}/api/submissions`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? "Upload failed.");
  }

  return res.json();
}
