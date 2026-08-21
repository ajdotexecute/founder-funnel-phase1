import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary";

export function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  const base = "rounded-lg px-5 py-2.5 font-medium transition disabled:opacity-40 disabled:cursor-not-allowed";
  const styles =
    variant === "primary"
      ? "bg-steel text-white hover:bg-steel/90"
      : "bg-transparent border border-white/20 text-white hover:bg-white/5";

  return <button className={`${base} ${styles} ${className}`} {...props} />;
}
