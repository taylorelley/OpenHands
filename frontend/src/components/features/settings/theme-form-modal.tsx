import { useState } from "react";
import { useTranslation } from "react-i18next";
import { BrandButton } from "#/components/features/settings/brand-button";
import { SettingsInput } from "#/components/features/settings/settings-input";
import { ProfileNameInput } from "#/components/features/settings/profile-name-input";
import { LoadingSpinner } from "#/components/shared/loading-spinner";
import { ApiKeyModalBase } from "#/components/features/settings/api-key-modal-base";
import {
  ThemeSummary,
  ThemeConfig,
} from "#/api/settings-service/themes-service.api";
import { useSaveTheme } from "#/hooks/mutation/use-save-theme";
import { displayErrorToast } from "#/utils/custom-toast-handlers";
import { mutateWithToast } from "#/utils/mutate-with-toast";
import { extractErrorMessage } from "#/utils/extract-error-message";
import { I18nKey } from "#/i18n/declaration";
import { PROFILE_NAME_PATTERN } from "#/utils/derive-profile-name";

interface ThemeFormModalProps {
  mode: "create" | "edit";
  theme: ThemeSummary | null;
  onClose: () => void;
}

const EMPTY_CONFIG: ThemeConfig = {
  primary: "",
  base: "",
  base_secondary: "",
  content: "",
  app_name: "",
  logo_url: "",
};

export function ThemeFormModal({ mode, theme, onClose }: ThemeFormModalProps) {
  const { t } = useTranslation();
  const saveTheme = useSaveTheme();
  const [name, setName] = useState(theme?.name ?? "");
  const [config, setConfig] = useState<ThemeConfig>(
    theme
      ? {
          primary: theme.primary ?? "",
          base: theme.base ?? "",
          base_secondary: theme.base_secondary ?? "",
          content: theme.content ?? "",
          app_name: theme.app_name ?? "",
          logo_url: theme.logo_url ?? "",
        }
      : EMPTY_CONFIG,
  );

  const trimmedName = name.trim();
  const isNameValid = mode === "edit" || PROFILE_NAME_PATTERN.test(trimmedName);

  const updateField = (key: keyof ThemeConfig) => (value: string) => {
    setConfig((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async () => {
    if (!isNameValid) {
      displayErrorToast(t(I18nKey.SETTINGS$PROFILE_NAME_RULE));
      return;
    }
    const targetName = mode === "create" ? trimmedName : (theme?.name ?? "");
    const request = {
      theme: {
        primary: config.primary?.trim() || null,
        base: config.base?.trim() || null,
        base_secondary: config.base_secondary?.trim() || null,
        content: config.content?.trim() || null,
        app_name: config.app_name?.trim() || null,
        logo_url: config.logo_url?.trim() || null,
      },
    };
    const ok = await mutateWithToast(
      saveTheme,
      { name: targetName, request },
      {
        success: t(
          mode === "create"
            ? I18nKey.SETTINGS$THEME_CREATED
            : I18nKey.SETTINGS$THEME_UPDATED,
          { name: targetName },
        ),
        error: (err) => extractErrorMessage(err, t(I18nKey.ERROR$GENERIC)),
      },
    ).catch(() => null);
    if (ok !== null) onClose();
  };

  const footer = (
    <>
      <BrandButton
        testId="theme-form-submit"
        type="button"
        variant="primary"
        className="grow"
        onClick={handleSubmit}
        isDisabled={saveTheme.isPending || !isNameValid}
      >
        {saveTheme.isPending ? (
          <LoadingSpinner size="small" />
        ) : (
          t(I18nKey.BUTTON$SAVE)
        )}
      </BrandButton>
      <BrandButton
        type="button"
        variant="secondary"
        className="grow"
        onClick={onClose}
        isDisabled={saveTheme.isPending}
      >
        {t(I18nKey.BUTTON$CANCEL)}
      </BrandButton>
    </>
  );

  return (
    <ApiKeyModalBase
      isOpen
      title={t(
        mode === "create"
          ? I18nKey.SETTINGS$THEME_CREATE_TITLE
          : I18nKey.SETTINGS$THEME_EDIT_TITLE,
      )}
      footer={footer}
    >
      <div data-testid="theme-form-modal" className="flex flex-col gap-3">
        {mode === "create" && (
          <ProfileNameInput
            testId="theme-name-input"
            ruleTestId="theme-name-rule"
            value={name}
            onChange={setName}
          />
        )}
        <div className="grid grid-cols-2 gap-3">
          <SettingsInput
            testId="theme-primary-input"
            label={t(I18nKey.SETTINGS$THEME_PRIMARY_COLOR)}
            type="color"
            className="w-full"
            value={config.primary || "#000000"}
            onChange={updateField("primary")}
          />
          <SettingsInput
            testId="theme-base-input"
            label={t(I18nKey.SETTINGS$THEME_BASE_COLOR)}
            type="color"
            className="w-full"
            value={config.base || "#000000"}
            onChange={updateField("base")}
          />
          <SettingsInput
            testId="theme-base-secondary-input"
            label={t(I18nKey.SETTINGS$THEME_BASE_SECONDARY_COLOR)}
            type="color"
            className="w-full"
            value={config.base_secondary || "#000000"}
            onChange={updateField("base_secondary")}
          />
          <SettingsInput
            testId="theme-content-input"
            label={t(I18nKey.SETTINGS$THEME_CONTENT_COLOR)}
            type="color"
            className="w-full"
            value={config.content || "#000000"}
            onChange={updateField("content")}
          />
        </div>
        <SettingsInput
          testId="theme-app-name-input"
          label={t(I18nKey.SETTINGS$THEME_APP_NAME)}
          type="text"
          className="w-full"
          value={config.app_name || ""}
          placeholder="OpenHands"
          onChange={updateField("app_name")}
        />
        <SettingsInput
          testId="theme-logo-url-input"
          label={t(I18nKey.SETTINGS$THEME_LOGO_URL)}
          type="url"
          className="w-full"
          value={config.logo_url || ""}
          placeholder="https://example.com/logo.png"
          onChange={updateField("logo_url")}
        />
      </div>
    </ApiKeyModalBase>
  );
}
