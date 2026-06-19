import { useMutation, useQueryClient } from "@tanstack/react-query";
import ThemesService, {
  SaveThemeRequest,
} from "#/api/settings-service/themes-service.api";
import { THEMES_QUERY_KEY } from "#/hooks/query/use-themes";
import { SETTINGS_QUERY_KEYS } from "#/hooks/query/query-keys";

interface SaveThemeVariables {
  name: string;
  request?: SaveThemeRequest;
}

export function useSaveTheme() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ name, request }: SaveThemeVariables) => {
      await ThemesService.saveTheme(name, request ?? {});
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [THEMES_QUERY_KEY] });
      // Saving a theme that happens to be the active one changes the colors
      // ``use-apply-theme`` reads off the settings cache.
      queryClient.invalidateQueries({ queryKey: SETTINGS_QUERY_KEYS.all });
    },
  });
}
