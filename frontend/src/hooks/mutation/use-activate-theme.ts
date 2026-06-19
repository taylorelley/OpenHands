import { useMutation, useQueryClient } from "@tanstack/react-query";
import ThemesService from "#/api/settings-service/themes-service.api";
import { THEMES_QUERY_KEY } from "#/hooks/query/use-themes";
import { SETTINGS_QUERY_KEYS } from "#/hooks/query/query-keys";

export function useActivateTheme() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (name: string) => {
      await ThemesService.activateTheme(name);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [THEMES_QUERY_KEY] });
      // Runtime theme application reads ``theme_profiles.active`` off the
      // main settings cache, not ``useThemes()`` — must refetch both.
      queryClient.invalidateQueries({ queryKey: SETTINGS_QUERY_KEYS.all });
    },
  });
}
