import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { ThemeSummary } from "#/api/settings-service/themes-service.api";
import { ThemesBody } from "#/components/features/settings/themes-body";

const themes: ThemeSummary[] = [
  {
    name: "t1",
    primary: "#ff0000",
    base: null,
    base_secondary: null,
    content: null,
    app_name: null,
    logo_url: null,
  },
  {
    name: "t2",
    primary: null,
    base: null,
    base_secondary: null,
    content: null,
    app_name: null,
    logo_url: null,
  },
];

describe("ThemesBody", () => {
  it("shows a loading spinner while isLoading is true", () => {
    render(
      <ThemesBody
        isLoading
        loadError={null}
        themes={[]}
        active={null}
        onActivate={vi.fn()}
        onEdit={vi.fn()}
        onRename={vi.fn()}
        onDelete={vi.fn()}
        isActivating={false}
      />,
    );

    expect(screen.getByTestId("loading-spinner")).toBeInTheDocument();
  });

  it("shows the load-error paragraph when loadError is set", () => {
    render(
      <ThemesBody
        isLoading={false}
        loadError={new Error("boom")}
        themes={[]}
        active={null}
        onActivate={vi.fn()}
        onEdit={vi.fn()}
        onRename={vi.fn()}
        onDelete={vi.fn()}
        isActivating={false}
      />,
    );

    expect(screen.getByText("SETTINGS$THEMES_LOAD_ERROR")).toBeInTheDocument();
  });

  it("shows the empty-state paragraph when no themes are passed", () => {
    render(
      <ThemesBody
        isLoading={false}
        loadError={null}
        themes={[]}
        active={null}
        onActivate={vi.fn()}
        onEdit={vi.fn()}
        onRename={vi.fn()}
        onDelete={vi.fn()}
        isActivating={false}
      />,
    );

    expect(screen.getByText("SETTINGS$THEMES_EMPTY")).toBeInTheDocument();
  });

  it("renders one ThemeRow per theme and marks the active one", () => {
    render(
      <ThemesBody
        isLoading={false}
        loadError={null}
        themes={themes}
        active="t1"
        onActivate={vi.fn()}
        onEdit={vi.fn()}
        onRename={vi.fn()}
        onDelete={vi.fn()}
        isActivating={false}
      />,
    );

    const rows = screen.getAllByTestId("theme-row");
    expect(rows).toHaveLength(2);
    expect(rows[0]).toHaveTextContent("t1");
    expect(rows[0]).toHaveTextContent("SETTINGS$THEME_ACTIVE_BADGE");
    expect(rows[1]).not.toHaveTextContent("SETTINGS$THEME_ACTIVE_BADGE");
  });
});
