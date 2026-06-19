import { NavLink } from "react-router";
import { useTranslation } from "react-i18next";
import OpenHandsLogo from "#/assets/branding/openhands-logo.svg?react";
import { I18nKey } from "#/i18n/declaration";
import { StyledTooltip } from "#/components/shared/buttons/styled-tooltip";
import { useSettings } from "#/hooks/query/use-settings";

export function OpenHandsLogoButton() {
  const { t } = useTranslation();
  const { data: settings } = useSettings();

  const tooltipText = t(I18nKey.BRANDING$OPENHANDS);
  const ariaLabel = t(I18nKey.BRANDING$OPENHANDS_LOGO);

  const themeProfiles = settings?.theme_profiles;
  const activeTheme = themeProfiles?.active
    ? themeProfiles.profiles[themeProfiles.active]
    : undefined;
  const logoUrl = activeTheme?.logo_url;

  return (
    <StyledTooltip content={tooltipText}>
      <NavLink to="/" aria-label={ariaLabel}>
        {logoUrl ? (
          <img src={logoUrl} alt={ariaLabel} width={46} height={30} />
        ) : (
          <OpenHandsLogo width={46} height={30} />
        )}
      </NavLink>
    </StyledTooltip>
  );
}
