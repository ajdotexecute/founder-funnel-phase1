import { useEffect, useState } from "react";

import { API_URL } from "./api";

export interface Theme {
  product_name: string;
  primary: string;
  secondary: string;
  accent: string;
  background: string;
  text: string;
  font_family: string;
  font_family_display: string;
  font_family_mono: string;
  logo_path: string | null;
  footer_text: string | null;
  logo_url: string | null;
}

function hexToRgbChannels(hex: string): string | null {
  const match = /^#?([0-9a-f]{6})$/i.exec(hex.trim());
  if (!match) return null;
  const n = parseInt(match[1], 16);
  return `${(n >> 16) & 255} ${(n >> 8) & 255} ${n & 255}`;
}

function applyTheme(theme: Theme) {
  const root = document.documentElement.style;
  const bg = hexToRgbChannels(theme.background);
  const accent = hexToRgbChannels(theme.accent);
  if (bg) root.setProperty("--color-background", bg);
  if (accent) root.setProperty("--color-accent", accent);
  root.setProperty("--font-family", theme.font_family);
  root.setProperty("--font-family-display", theme.font_family_display);
  root.setProperty("--font-family-mono", theme.font_family_mono);
}

export function useTheme(): Theme | null {
  const [theme, setTheme] = useState<Theme | null>(null);

  useEffect(() => {
    fetch(`${API_URL}/api/theme`)
      .then((res) => res.json())
      .then((data: Theme) => {
        applyTheme(data);
        setTheme(data);
      })
      .catch(() => {
        // Network hiccup fetching the theme — keep the neutral CSS defaults
        // already in index.css rather than leaving the page unstyled.
      });
  }, []);

  return theme;
}
