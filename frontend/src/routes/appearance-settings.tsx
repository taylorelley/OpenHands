import { useTranslation } from "react-i18next";
import { ThemesManager } from "#/components/features/settings/themes-manager";
import { I18nKey } from "#/i18n/declaration";

function AppearanceSettingsScreen() {
  const { t } = useTranslation();

  return (
    <div
      data-testid="appearance-settings-screen"
      className="flex flex-col h-full"
    >
      <p className="text-xs mb-4">
        {t(I18nKey.SETTINGS$APPEARANCE_DESCRIPTION)}
      </p>

      <div className="flex-1 overflow-auto custom-scrollbar-always">
        <ThemesManager />
      </div>
    </div>
  );
}

export default AppearanceSettingsScreen;
