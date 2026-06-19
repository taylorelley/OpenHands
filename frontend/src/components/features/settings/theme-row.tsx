import { useState } from "react";
import { useTranslation } from "react-i18next";
import { ThemeActionsMenu } from "#/components/features/settings/theme-actions-menu";
import { ThemeSummary } from "#/api/settings-service/themes-service.api";
import { I18nKey } from "#/i18n/declaration";
import { Typography } from "#/ui/typography";
import ThreeDotsVerticalIcon from "#/icons/three-dots-vertical.svg?react";

interface ThemeRowProps {
  theme: ThemeSummary;
  isActive: boolean;
  onActivate: (name: string) => void;
  onEdit: (theme: ThemeSummary) => void;
  onRename: (theme: ThemeSummary) => void;
  onDelete: (theme: ThemeSummary) => void;
  isActivating: boolean;
}

const SWATCH_KEYS = ["primary", "base", "base_secondary", "content"] as const;

export function ThemeRow({
  theme,
  isActive,
  onActivate,
  onEdit,
  onRename,
  onDelete,
  isActivating,
}: ThemeRowProps) {
  const { t } = useTranslation();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div
      data-testid="theme-row"
      className="flex items-center justify-between gap-3 px-5 py-4"
    >
      <div className="flex flex-col gap-1 min-w-0 flex-1 sm:flex-row sm:items-center sm:gap-3">
        <Typography.Text
          className="font-medium text-white truncate min-w-0 max-w-full"
          title={theme.name}
        >
          {theme.name}
        </Typography.Text>
        <div className="flex items-center gap-1" data-testid="theme-swatches">
          {SWATCH_KEYS.map((key) => (
            <span
              key={key}
              title={key}
              className="w-4 h-4 rounded-full border border-tertiary shrink-0"
              style={{ backgroundColor: theme[key] || "transparent" }}
            />
          ))}
        </div>
        {isActive && (
          <Typography.Text
            className="text-xs bg-primary text-[#0D0F11] font-semibold rounded-full px-2 py-0.5 whitespace-nowrap self-start sm:self-auto"
            testId="theme-active-badge"
          >
            {t(I18nKey.SETTINGS$THEME_ACTIVE_BADGE)}
          </Typography.Text>
        )}
      </div>
      <div className="relative shrink-0">
        <button
          type="button"
          onClick={() => setMenuOpen((open) => !open)}
          aria-label={t(I18nKey.SETTINGS$THEME_MENU)}
          className="cursor-pointer text-gray-300 hover:text-white p-2 border border-tertiary rounded-md"
          data-testid="theme-menu-trigger"
        >
          <ThreeDotsVerticalIcon width={16} height={16} />
        </button>
        {menuOpen && (
          <ThemeActionsMenu
            onEdit={() => onEdit(theme)}
            onRename={() => onRename(theme)}
            onSetActive={() => onActivate(theme.name)}
            onDelete={() => onDelete(theme)}
            isActive={isActive}
            isActivating={isActivating}
            onClose={() => setMenuOpen(false)}
          />
        )}
      </div>
    </div>
  );
}
