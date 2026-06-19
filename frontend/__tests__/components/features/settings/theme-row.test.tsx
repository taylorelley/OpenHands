import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { ThemeSummary } from "#/api/settings-service/themes-service.api";
import { ThemeRow } from "#/components/features/settings/theme-row";

const theme: ThemeSummary = {
  name: "my-theme",
  primary: "#ff0000",
  base: null,
  base_secondary: null,
  content: null,
  app_name: null,
  logo_url: null,
};

function renderRow(
  overrides: Partial<React.ComponentProps<typeof ThemeRow>> = {},
) {
  const props = {
    theme,
    isActive: false,
    onActivate: vi.fn(),
    onEdit: vi.fn(),
    onRename: vi.fn(),
    onDelete: vi.fn(),
    isActivating: false,
    ...overrides,
  };
  return {
    // eslint-disable-next-line react/jsx-props-no-spreading
    ...render(<ThemeRow {...props} />),
    props,
  };
}

describe("ThemeRow", () => {
  it("renders the theme name and swatches", () => {
    renderRow();

    expect(screen.getByText("my-theme")).toBeInTheDocument();
    expect(screen.getByTestId("theme-swatches")).toBeInTheDocument();
    expect(screen.queryByTestId("theme-active-badge")).not.toBeInTheDocument();
  });

  it("shows the active badge when isActive is true", () => {
    renderRow({ isActive: true });

    expect(screen.getByTestId("theme-active-badge")).toHaveTextContent(
      "SETTINGS$THEME_ACTIVE_BADGE",
    );
  });

  it("opens the actions menu when the trigger is clicked", async () => {
    renderRow();
    const user = userEvent.setup();

    expect(screen.queryByTestId("theme-edit")).not.toBeInTheDocument();
    await user.click(screen.getByTestId("theme-menu-trigger"));
    expect(screen.getByTestId("theme-edit")).toBeInTheDocument();
  });

  it("calls onDelete when the delete menu item is clicked", async () => {
    const onDelete = vi.fn();
    renderRow({ onDelete });
    const user = userEvent.setup();

    await user.click(screen.getByTestId("theme-menu-trigger"));
    await user.click(screen.getByTestId("theme-delete"));

    expect(onDelete).toHaveBeenCalledWith(theme);
  });
});
