import type { InputHTMLAttributes } from "react";

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={`w-full rounded-lg border border-white/15 bg-black/30 px-4 py-2.5 text-white placeholder:text-white/30 outline-none focus:border-steel ${props.className ?? ""}`}
    />
  );
}
