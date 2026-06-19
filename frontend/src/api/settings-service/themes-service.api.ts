import { openHands } from "../open-hands-axios";

export interface ThemeSummary {
  name: string;
  primary: string | null;
  base: string | null;
  base_secondary: string | null;
  content: string | null;
  app_name: string | null;
  logo_url: string | null;
}

// Not exported — only `listThemes` reads it as its response shape.
interface ThemeListResponse {
  themes: ThemeSummary[];
  active_theme: string | null;
}

export interface ThemeConfig {
  primary?: string | null;
  base?: string | null;
  base_secondary?: string | null;
  content?: string | null;
  app_name?: string | null;
  logo_url?: string | null;
}

export interface ThemeDetailResponse {
  name: string;
  config: ThemeConfig;
}

export interface SaveThemeRequest {
  theme?: ThemeConfig;
}

class ThemesService {
  static async listThemes(): Promise<ThemeListResponse> {
    const { data } = await openHands.get<ThemeListResponse>(
      "/api/v1/settings/themes",
    );
    return data;
  }

  static async getTheme(name: string): Promise<ThemeDetailResponse> {
    const { data } = await openHands.get<ThemeDetailResponse>(
      `/api/v1/settings/themes/${encodeURIComponent(name)}`,
    );
    return data;
  }

  static async saveTheme(
    name: string,
    request: SaveThemeRequest = {},
  ): Promise<void> {
    await openHands.post(
      `/api/v1/settings/themes/${encodeURIComponent(name)}`,
      request,
    );
  }

  static async deleteTheme(name: string): Promise<void> {
    await openHands.delete(
      `/api/v1/settings/themes/${encodeURIComponent(name)}`,
    );
  }

  static async activateTheme(name: string): Promise<void> {
    await openHands.post(
      `/api/v1/settings/themes/${encodeURIComponent(name)}/activate`,
    );
  }

  static async renameTheme(name: string, newName: string): Promise<void> {
    await openHands.post(
      `/api/v1/settings/themes/${encodeURIComponent(name)}/rename`,
      { new_name: newName },
    );
  }
}

export default ThemesService;
