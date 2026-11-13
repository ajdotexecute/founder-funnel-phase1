import type { PropsWithChildren } from "react";

import { API_URL } from "../lib/api";
import { useTheme } from "../lib/theme";

export function SiteChrome({ children }: PropsWithChildren) {
  const theme = useTheme();

  return (
    <div className="flex min-h-screen flex-col">
      {theme && (theme.logo_url || theme.product_name) && (
        <header className="flex items-center gap-3 border-b border-white/10 px-6 py-3">
          {theme.logo_url && (
            <img
              src={`${API_URL}${theme.logo_url}`}
              alt={theme.product_name}
              className="h-6 w-auto"
              onError={(e) => {
                e.currentTarget.style.display = "none";
              }}
            />
          )}
          <span className="text-sm font-semibold text-white/70">{theme.product_name}</span>
        </header>
      )}

      <div className="flex-1">{children}</div>

      {theme?.footer_text && (
        <footer className="border-t border-white/10 px-6 py-4 text-center text-xs text-white/40">
          {theme.footer_text}
        </footer>
      )}
    </div>
  );
}
