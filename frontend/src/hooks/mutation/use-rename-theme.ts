import { useMutation, useQueryClient } from "@tanstack/react-query";
import ThemesService from "#/api/settings-service/themes-service.api";
import { THEMES_QUERY_KEY } from "#/hooks/query/use-themes";
import { SETTINGS_QUERY_KEYS } from "#/hooks/query/query-keys";

interface RenameThemeVariables {
  name: string;
  newName: string;
}

export function useRenameTheme() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ name, newName }: RenameThemeVariables) => {
      await ThemesService.renameTheme(name, newName);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [THEMES_QUERY_KEY] });
      // Renaming the active theme changes ``theme_profiles.active`` to the
      // new name; the settings cache must refetch so any UI that reads the
      // active-theme name stays in sync.
      queryClient.invalidateQueries({ queryKey: SETTINGS_QUERY_KEYS.all });
    },
  });
}
