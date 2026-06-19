import { useTranslation } from "react-i18next";
import { BrandButton } from "#/components/features/settings/brand-button";
import { LoadingSpinner } from "#/components/shared/loading-spinner";
import { ApiKeyModalBase } from "#/components/features/settings/api-key-modal-base";
import { ThemeSummary } from "#/api/settings-service/themes-service.api";
import { useDeleteTheme } from "#/hooks/mutation/use-delete-theme";
import { mutateWithToast } from "#/utils/mutate-with-toast";
import { extractErrorMessage } from "#/utils/extract-error-message";
import { I18nKey } from "#/i18n/declaration";
import { Typography } from "#/ui/typography";

interface DeleteThemeModalProps {
  theme: ThemeSummary | null;
  onClose: () => void;
}

export function DeleteThemeModal({ theme, onClose }: DeleteThemeModalProps) {
  const { t } = useTranslation();
  const deleteTheme = useDeleteTheme();

  if (!theme) return null;

  const handleDelete = async () => {
    const ok = await mutateWithToast(deleteTheme, theme.name, {
      success: t(I18nKey.SETTINGS$THEME_DELETED, { name: theme.name }),
      error: (err) => extractErrorMessage(err, t(I18nKey.ERROR$GENERIC)),
    }).catch(() => null);
    if (ok !== null) onClose();
  };

  const footer = (
    <>
      <BrandButton
        testId="delete-theme-confirm"
        type="button"
        variant="danger"
        className="grow"
        onClick={handleDelete}
        isDisabled={deleteTheme.isPending}
      >
        {deleteTheme.isPending ? (
          <LoadingSpinner size="small" />
        ) : (
          t(I18nKey.BUTTON$DELETE)
        )}
      </BrandButton>
      <BrandButton
        type="button"
        variant="secondary"
        className="grow"
        onClick={onClose}
        isDisabled={deleteTheme.isPending}
      >
        {t(I18nKey.BUTTON$CANCEL)}
      </BrandButton>
    </>
  );

  return (
    <ApiKeyModalBase
      isOpen
      title={t(I18nKey.SETTINGS$THEME_DELETE_TITLE)}
      footer={footer}
    >
      <Typography.Paragraph className="text-sm break-all">
        {t(I18nKey.SETTINGS$THEME_DELETE_CONFIRMATION, {
          name: theme.name,
        })}
      </Typography.Paragraph>
    </ApiKeyModalBase>
  );
}
