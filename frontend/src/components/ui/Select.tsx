import type { SelectHTMLAttributes } from "react";

export function Select(props: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      className={`w-full rounded-lg border border-white/15 bg-black/30 px-4 py-2.5 text-white outline-none focus:border-steel ${props.className ?? ""}`}
    />
  );
}
