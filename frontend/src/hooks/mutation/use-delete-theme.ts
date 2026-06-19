import { useMutation, useQueryClient } from "@tanstack/react-query";
import ThemesService from "#/api/settings-service/themes-service.api";
import { THEMES_QUERY_KEY } from "#/hooks/query/use-themes";
import { SETTINGS_QUERY_KEYS } from "#/hooks/query/query-keys";

export function useDeleteTheme() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (name: string) => {
      await ThemesService.deleteTheme(name);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [THEMES_QUERY_KEY] });
      // Deleting the active theme clears ``theme_profiles.active`` server-side;
      // the settings cache must refetch or the page keeps the deleted
      // theme's colors applied.
      queryClient.invalidateQueries({ queryKey: SETTINGS_QUERY_KEYS.all });
    },
  });
}
