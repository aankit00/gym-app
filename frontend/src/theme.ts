// Design tokens for GymProof (light only). Keys match the "color" block of /app/design_guidelines.json.
import { useMemo } from "react";
import { Appearance, StyleSheet, useColorScheme } from "react-native";

export type ColorScheme = "light" | "dark";

const light = {
  surface: "#F2F2F7",
  onSurface: "#111118",
  surfaceSecondary: "#FFFFFF",
  onSurfaceSecondary: "#111118",
  surfaceTertiary: "#E5E5EA",
  onSurfaceTertiary: "#3A3A3C",
  surfaceInverse: "#18161B",
  onSurfaceInverse: "#FFFFFF",
  muted: "#8E8E93",

  brand: "#F5A623",
  onBrand: "#FFFFFF",
  brandPrimary: "#FF9F0A",
  onBrandPrimary: "#FFFFFF",
  brandSecondary: "#FFD60A",
  onBrandSecondary: "#18161B",
  brandTertiary: "#FFF4CE",
  onBrandTertiary: "#C77700",

  success: "#34C759",
  onSuccess: "#FFFFFF",
  warning: "#FFD60A",
  onWarning: "#18161B",
  error: "#FF3B30",
  onError: "#FFFFFF",
  info: "#0A84FF",
  onInfo: "#FFFFFF",

  border: "#E5E5EA",
  borderStrong: "#C7C7CC",
  divider: "#E5E5EA",
  scrim: "rgba(0,0,0,0.55)",
};

export type ThemeColors = typeof light;

export const defaultScheme = "light" satisfies ColorScheme;

export const themes: { light: ThemeColors; dark?: ThemeColors } = { light };

export const spacing = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, "2xl": 32, "3xl": 48 };
export const radius = { sm: 6, md: 12, lg: 20, pill: 999 };

export function setColorScheme(scheme: ColorScheme | null) {
  Appearance.setColorScheme?.(scheme ?? "unspecified");
}

setColorScheme?.(themes.dark ? null : defaultScheme);

export function useTheme(): { scheme: ColorScheme; colors: ThemeColors } {
  const system = useColorScheme();
  const scheme: ColorScheme = (system === "light" || system === "dark") && themes[system] ? system : defaultScheme;
  return { scheme, colors: themes[scheme] ?? themes.light };
}

export function makeStyles<T extends StyleSheet.NamedStyles<T> | StyleSheet.NamedStyles<any>>(
  factory: (colors: ThemeColors) => T & StyleSheet.NamedStyles<any>,
): () => T {
  return function useStyles(): T {
    const { colors } = useTheme();
    return useMemo(() => StyleSheet.create(factory(colors)), [colors]);
  };
}
