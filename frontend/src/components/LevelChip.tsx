import React, { useEffect, useState } from "react";
import { Text, View } from "react-native";
import { Image } from "expo-image";
import { Ionicons } from "@react-native-vector-icons/ionicons";
import type { Level } from "@/src/api";
import { makeStyles, radius, useTheme } from "@/src/theme";

const LABEL: Record<Level, string> = { beginner: "Beginner", intermediate: "Intermediate", pro: "Pro" };

export function LevelChip({ level, testID }: { level: Level; testID?: string }) {
  const styles = useStyles();
  const { colors } = useTheme();
  const bg = level === "beginner" ? colors.success : level === "intermediate" ? colors.brandPrimary : colors.surfaceInverse;
  // dark text on green/amber: white on these is too faint to read at chip size
  const fg = level === "pro" ? colors.onSurfaceInverse : colors.onSurface;
  return (
    <View testID={testID} style={[styles.chip, { backgroundColor: bg }]}>
      <Text style={[styles.text, { color: fg }]}>{LABEL[level]}</Text>
    </View>
  );
}

// Still thumbnail for lists: the WorkoutX poster, a photo, or a muscle icon when neither is available.
export function ExerciseThumb({ uri, size = 72, testID }: { uri: string | null; size?: number; testID?: string }) {
  const styles = useStyles();
  const { colors } = useTheme();
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [uri]);
  return uri && !failed ? (
    <Image testID={testID} source={{ uri }} style={[styles.thumb, { width: size, height: size }]} contentFit="cover" transition={150}
      recyclingKey={uri} onError={() => setFailed(true)} />
  ) : (
    <View testID={testID} style={[styles.thumb, styles.empty, { width: size, height: size }]}>
      <Ionicons name="barbell" size={size / 2.6} color={colors.muted} />
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  chip: { alignSelf: "flex-start", paddingHorizontal: 8, height: 22, borderRadius: radius.sm, justifyContent: "center" },
  text: { fontSize: 11, fontWeight: "900", letterSpacing: 0.5 },
  thumb: { borderRadius: radius.md, backgroundColor: c.surfaceTertiary },
  empty: { alignItems: "center", justifyContent: "center" },
}));
