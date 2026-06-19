import { useState } from "react";
import { useTranslation } from "react-i18next";
import { BrandButton } from "#/components/features/settings/brand-button";
import { RenameThemeModal } from "#/components/features/settings/rename-theme-modal";
import { DeleteThemeModal } from "#/components/features/settings/delete-theme-modal";
import { ThemeFormModal } from "#/components/features/settings/theme-form-modal";
import { ThemesBody } from "#/components/features/settings/themes-body";
import { ThemeSummary } from "#/api/settings-service/themes-service.api";
import { useThemes } from "#/hooks/query/use-themes";
import { useActivateTheme } from "#/hooks/mutation/use-activate-theme";
import { mutateWithToast } from "#/utils/mutate-with-toast";
import { extractErrorMessage } from "#/utils/extract-error-message";
import { I18nKey } from "#/i18n/declaration";

export function ThemesManager() {
  const { t } = useTranslation();
  const { data, isLoading, error } = useThemes();
  const activateTheme = useActivateTheme();
  const [themeToRename, setThemeToRename] = useState<ThemeSummary | null>(null);
  const [themeToDelete, setThemeToDelete] = useState<ThemeSummary | null>(null);
  const [formMode, setFormMode] = useState<"create" | "edit" | null>(null);
  const [themeToEdit, setThemeToEdit] = useState<ThemeSummary | null>(null);

  const themes = data?.themes ?? [];
  const active = data?.active_theme ?? null;

  const handleActivate = async (name: string) => {
    await mutateWithToast(activateTheme, name, {
      success: t(I18nKey.SETTINGS$THEME_ACTIVATED, { name }),
      error: (err) => extractErrorMessage(err, t(I18nKey.ERROR$GENERIC)),
    }).catch(() => null);
  };

  const handleAdd = () => {
    setThemeToEdit(null);
    setFormMode("create");
  };

  const handleEdit = (theme: ThemeSummary) => {
    setThemeToEdit(theme);
    setFormMode("edit");
  };

  const closeForm = () => {
    setFormMode(null);
    setThemeToEdit(null);
  };

  return (
    <>
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-base font-semibold text-white">
            {t(I18nKey.SETTINGS$AVAILABLE_THEMES)}
          </h2>
          <BrandButton
            testId="add-theme"
            type="button"
            variant="primary"
            className="ml-auto"
            onClick={handleAdd}
          >
            {t(I18nKey.SETTINGS$ADD_THEME)}
          </BrandButton>
        </div>

        <ThemesBody
          isLoading={isLoading}
          loadError={error ?? null}
          themes={themes}
          active={active}
          onActivate={handleActivate}
          onEdit={handleEdit}
          onRename={setThemeToRename}
          onDelete={setThemeToDelete}
          isActivating={activateTheme.isPending}
        />
      </div>

      {formMode && (
        <ThemeFormModal
          mode={formMode}
          theme={themeToEdit}
          onClose={closeForm}
        />
      )}
      <RenameThemeModal
        theme={themeToRename}
        onClose={() => setThemeToRename(null)}
      />
      <DeleteThemeModal
        theme={themeToDelete}
        onClose={() => setThemeToDelete(null)}
      />
    </>
  );
}
