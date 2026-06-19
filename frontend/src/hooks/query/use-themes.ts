import { useQuery } from "@tanstack/react-query";
import ThemesService from "#/api/settings-service/themes-service.api";
import { useIsAuthed } from "./use-is-authed";

export const THEMES_QUERY_KEY = "themes";

export function useThemes() {
  const { data: userIsAuthenticated } = useIsAuthed();

  return useQuery({
    queryKey: [THEMES_QUERY_KEY],
    queryFn: ThemesService.listThemes,
    enabled: !!userIsAuthenticated,
    retry: (_, error) => error.status !== 404,
    staleTime: 1000 * 60 * 5,
    gcTime: 1000 * 60 * 15,
    meta: { disableToast: true },
  });
}
