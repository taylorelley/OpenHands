import React from "react";
import { useSettings } from "#/hooks/query/use-settings";
import { Theme } from "#/types/settings";

const CSS_VARS_BY_THEME_KEY: Record<
  keyof Pick<Theme, "primary" | "base" | "base_secondary" | "content">,
  string
> = {
  primary: "--color-primary",
  base: "--color-base",
  base_secondary: "--color-base-secondary",
  content: "--color-content",
};

/**
 * Applies the active custom theme's core colors as CSS custom property
 * overrides on `<html>`. Unset fields `removeProperty` so they fall back to
 * the built-in `@theme` default in `tailwind.css`.
 */
export function useApplyTheme() {
  const { data: settings } = useSettings();

  React.useEffect(() => {
    const themeProfiles = settings?.theme_profiles;
    const active = themeProfiles?.active;
    const theme = active ? themeProfiles?.profiles[active] : undefined;

    const root = document.documentElement;
    (
      Object.keys(CSS_VARS_BY_THEME_KEY) as Array<
        keyof typeof CSS_VARS_BY_THEME_KEY
      >
    ).forEach((key) => {
      const cssVar = CSS_VARS_BY_THEME_KEY[key];
      const value = theme?.[key];
      if (value) {
        root.style.setProperty(cssVar, value);
      } else {
        root.style.removeProperty(cssVar);
      }
    });
  }, [settings?.theme_profiles]);
}
