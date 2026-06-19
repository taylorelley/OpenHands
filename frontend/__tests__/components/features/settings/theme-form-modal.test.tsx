import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import type { ThemeSummary } from "#/api/settings-service/themes-service.api";
import { ThemeFormModal } from "#/components/features/settings/theme-form-modal";

const saveMock = vi.fn();
vi.mock("#/hooks/mutation/use-save-theme", () => ({
  useSaveTheme: () => ({ mutateAsync: saveMock, isPending: false }),
}));

const toastMocks = vi.hoisted(() => ({
  displayErrorToast: vi.fn(),
  displaySuccessToast: vi.fn(),
}));
vi.mock("#/utils/custom-toast-handlers", () => toastMocks);

const theme: ThemeSummary = {
  name: "my-theme",
  primary: "#ff0000",
  base: null,
  base_secondary: null,
  content: null,
  app_name: "My App",
  logo_url: null,
};

beforeEach(() => {
  saveMock.mockReset().mockResolvedValue(undefined);
  toastMocks.displayErrorToast.mockReset();
  toastMocks.displaySuccessToast.mockReset();
});

describe("ThemeFormModal", () => {
  it("renders a name input in create mode", () => {
    render(<ThemeFormModal mode="create" theme={null} onClose={vi.fn()} />);

    expect(screen.getByTestId("theme-name-input")).toBeInTheDocument();
  });

  it("does not render a name input in edit mode", () => {
    render(<ThemeFormModal mode="edit" theme={theme} onClose={vi.fn()} />);

    expect(screen.queryByTestId("theme-name-input")).not.toBeInTheDocument();
  });

  it("prefills color and branding fields from the existing theme in edit mode", () => {
    render(<ThemeFormModal mode="edit" theme={theme} onClose={vi.fn()} />);

    expect(
      (screen.getByTestId("theme-primary-input") as HTMLInputElement).value,
    ).toBe("#ff0000");
    expect(
      (screen.getByTestId("theme-app-name-input") as HTMLInputElement).value,
    ).toBe("My App");
  });

  it("submits the trimmed name and config on create", async () => {
    const onClose = vi.fn();
    render(<ThemeFormModal mode="create" theme={null} onClose={onClose} />);
    const user = userEvent.setup();

    await user.type(screen.getByTestId("theme-name-input"), "  new-theme  ");
    await user.click(screen.getByTestId("theme-form-submit"));

    expect(saveMock).toHaveBeenCalledWith({
      name: "new-theme",
      request: {
        theme: {
          primary: null,
          base: null,
          base_secondary: null,
          content: null,
          app_name: null,
          logo_url: null,
        },
      },
    });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("disables submit when the create-mode name is invalid", async () => {
    render(<ThemeFormModal mode="create" theme={null} onClose={vi.fn()} />);
    const user = userEvent.setup();

    await user.type(screen.getByTestId("theme-name-input"), "has space");

    expect(screen.getByTestId("theme-form-submit")).toBeDisabled();
    expect(saveMock).not.toHaveBeenCalled();
  });

  it("submits using the existing theme's name in edit mode", async () => {
    const onClose = vi.fn();
    render(<ThemeFormModal mode="edit" theme={theme} onClose={onClose} />);

    await userEvent.click(screen.getByTestId("theme-form-submit"));

    expect(saveMock).toHaveBeenCalledWith(
      expect.objectContaining({ name: "my-theme" }),
    );
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
