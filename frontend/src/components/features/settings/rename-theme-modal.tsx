import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { BrandButton } from "#/components/features/settings/brand-button";
import { ProfileNameInput } from "#/components/features/settings/profile-name-input";
import { LoadingSpinner } from "#/components/shared/loading-spinner";
import { ApiKeyModalBase } from "#/components/features/settings/api-key-modal-base";
import { ThemeSummary } from "#/api/settings-service/themes-service.api";
import { useRenameTheme } from "#/hooks/mutation/use-rename-theme";
import { displayErrorToast } from "#/utils/custom-toast-handlers";
import { mutateWithToast } from "#/utils/mutate-with-toast";
import { extractErrorMessage } from "#/utils/extract-error-message";
import { I18nKey } from "#/i18n/declaration";
import { PROFILE_NAME_PATTERN } from "#/utils/derive-profile-name";

interface RenameThemeModalProps {
  theme: ThemeSummary | null;
  onClose: () => void;
}

export function RenameThemeModal({ theme, onClose }: RenameThemeModalProps) {
  const { t } = useTranslation();
  const [newName, setNewName] = useState("");
  const renameTheme = useRenameTheme();

  useEffect(() => {
    setNewName(theme?.name ?? "");
  }, [theme?.name]);

  if (!theme) return null;

  const trimmed = newName.trim();
  const isUnchanged = trimmed === theme.name;
  const isValid = PROFILE_NAME_PATTERN.test(trimmed);

  const handleSubmit = async () => {
    if (!isValid) {
      displayErrorToast(t(I18nKey.SETTINGS$PROFILE_NAME_RULE));
      return;
    }
    if (isUnchanged) {
      onClose();
      return;
    }
    const ok = await mutateWithToast(
      renameTheme,
      { name: theme.name, newName: trimmed },
      {
        success: t(I18nKey.SETTINGS$THEME_RENAMED, { name: trimmed }),
        error: (err) => extractErrorMessage(err, t(I18nKey.ERROR$GENERIC)),
      },
    ).catch(() => null);
    if (ok !== null) onClose();
  };

  const footer = (
    <>
      <BrandButton
        testId="rename-theme-submit"
        type="button"
        variant="primary"
        className="grow"
        onClick={handleSubmit}
        isDisabled={renameTheme.isPending || !isValid}
      >
        {renameTheme.isPending ? (
          <LoadingSpinner size="small" />
        ) : (
          t(I18nKey.BUTTON$RENAME)
        )}
      </BrandButton>
      <BrandButton
        type="button"
        variant="secondary"
        className="grow"
        onClick={onClose}
        isDisabled={renameTheme.isPending}
      >
        {t(I18nKey.BUTTON$CANCEL)}
      </BrandButton>
    </>
  );

  return (
    <ApiKeyModalBase
      isOpen
      title={t(I18nKey.SETTINGS$THEME_RENAME_TITLE)}
      footer={footer}
    >
      <div data-testid="rename-theme-modal" className="flex flex-col gap-3">
        <ProfileNameInput
          testId="rename-theme-input"
          ruleTestId="rename-theme-rule"
          value={newName}
          onChange={setNewName}
        />
      </div>
    </ApiKeyModalBase>
  );
}
