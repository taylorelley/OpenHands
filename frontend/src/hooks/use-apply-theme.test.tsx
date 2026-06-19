import { renderHook } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { useSettings } from "#/hooks/query/use-settings";
import { useApplyTheme } from "./use-apply-theme";
import { Settings } from "#/types/settings";

vi.mock("#/hooks/query/use-settings");

const mockUseSettings = vi.mocked(useSettings);

const baseSettings = {} as Settings;

describe("useApplyTheme", () => {
  beforeEach(() => {
    document.documentElement.style.removeProperty("--color-primary");
    document.documentElement.style.removeProperty("--color-base");
    document.documentElement.style.removeProperty("--color-base-secondary");
    document.documentElement.style.removeProperty("--color-content");
  });

  it("sets CSS custom properties from the active theme's colors", () => {
    mockUseSettings.mockReturnValue({
      data: {
        ...baseSettings,
        theme_profiles: {
          profiles: {
            mytheme: {
              primary: "#ff0000",
              base: "#00ff00",
              base_secondary: null,
              content: null,
              app_name: null,
              logo_url: null,
            },
          },
          active: "mytheme",
        },
      },
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    renderHook(() => useApplyTheme());

    expect(
      document.documentElement.style.getPropertyValue("--color-primary"),
    ).toBe("#ff0000");
    expect(
      document.documentElement.style.getPropertyValue("--color-base"),
    ).toBe("#00ff00");
    expect(
      document.documentElement.style.getPropertyValue("--color-base-secondary"),
    ).toBe("");
  });

  it("removes CSS custom properties when there is no active theme", () => {
    document.documentElement.style.setProperty("--color-primary", "#ff0000");

    mockUseSettings.mockReturnValue({
      data: {
        ...baseSettings,
        theme_profiles: { profiles: {}, active: null },
      },
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any);

    renderHook(() => useApplyTheme());

    expect(
      document.documentElement.style.getPropertyValue("--color-primary"),
    ).toBe("");
  });
});
