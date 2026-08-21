import type { PropsWithChildren } from "react";

export function Card({ children, className = "" }: PropsWithChildren<{ className?: string }>) {
  return (
    <div className={`rounded-xl border border-white/10 bg-white/5 p-6 ${className}`}>
      {children}
    </div>
  );
}
