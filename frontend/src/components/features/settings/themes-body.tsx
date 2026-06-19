import { useTranslation } from "react-i18next";
import { LoadingSpinner } from "#/components/shared/loading-spinner";
import { ThemeRow } from "#/components/features/settings/theme-row";
import { ThemeSummary } from "#/api/settings-service/themes-service.api";
import { I18nKey } from "#/i18n/declaration";
import { Typography } from "#/ui/typography";

interface ThemesBodyProps {
  isLoading: boolean;
  loadError: Error | null;
  themes: ThemeSummary[];
  active: string | null;
  onActivate: (name: string) => void;
  onEdit: (theme: ThemeSummary) => void;
  onRename: (theme: ThemeSummary) => void;
  onDelete: (theme: ThemeSummary) => void;
  isActivating: boolean;
}

export function ThemesBody({
  isLoading,
  loadError,
  themes,
  active,
  onActivate,
  onEdit,
  onRename,
  onDelete,
  isActivating,
}: ThemesBodyProps) {
  const { t } = useTranslation();

  if (isLoading) {
    return (
      <div className="flex justify-center p-4">
        <LoadingSpinner size="large" />
      </div>
    );
  }
  if (loadError) {
    return (
      <Typography.Paragraph className="text-sm text-red-400">
        {t(I18nKey.SETTINGS$THEMES_LOAD_ERROR)}
      </Typography.Paragraph>
    );
  }
  if (themes.length === 0) {
    return (
      <Typography.Paragraph className="text-sm text-gray-400 italic">
        {t(I18nKey.SETTINGS$THEMES_EMPTY)}
      </Typography.Paragraph>
    );
  }
  return (
    <div className="border border-tertiary rounded-md divide-y divide-tertiary">
      {themes.map((theme) => (
        <ThemeRow
          key={theme.name}
          theme={theme}
          isActive={theme.name === active}
          onActivate={onActivate}
          onEdit={onEdit}
          onRename={onRename}
          onDelete={onDelete}
          isActivating={isActivating}
        />
      ))}
    </div>
  );
}
