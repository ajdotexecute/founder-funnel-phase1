interface FileInputProps {
  label: string;
  required?: boolean;
  onChange: (file: File | null) => void;
  accept?: string;
}

export function FileInput({ label, required, onChange, accept }: FileInputProps) {
  return (
    <div>
      <label className="mb-1.5 block text-sm text-white/70">
        {label} {required ? <span className="text-steel">*</span> : <span className="text-white/40">(optional)</span>}
      </label>
      <input
        type="file"
        accept={accept}
        onChange={(e) => onChange(e.target.files?.[0] ?? null)}
        className="block w-full text-sm text-white/70 file:mr-4 file:rounded-lg file:border-0 file:bg-steel file:px-4 file:py-2 file:text-white file:cursor-pointer"
      />
    </div>
  );
}
