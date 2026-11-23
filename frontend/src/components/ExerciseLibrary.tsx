import React, { useCallback, useEffect, useMemo, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { FlashList } from "@shopify/flash-list";
import { useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Ionicons } from "@react-native-vector-icons/ionicons";
import { Level, Library, LibraryItem, useApi } from "@/src/api";
import { ExerciseThumb, LevelChip } from "@/src/components/LevelChip";
import { PrimaryButton } from "@/src/components/ui";
import { usesNativeTabs } from "@/src/navigation";
import { makeStyles, radius, spacing, useTheme } from "@/src/theme";

const LEVELS: { key: Level; label: string }[] = [
  { key: "beginner", label: "Beginner" }, { key: "intermediate", label: "Intermediate" }, { key: "pro", label: "Pro" },
];

type ChipGroup = { prefix: string; options: { key: string; label: string }[]; value: string; onChange: (k: string) => void; allLabel: string };

// One scrolling row of filter chips; several filters can share a row, separated by a divider.
function Chips({ groups }: { groups: ChipGroup[] }) {
  const styles = useStyles();
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chipRow} keyboardShouldPersistTaps="handled">
      {groups.map((g, gi) => (
        <React.Fragment key={g.prefix}>
          {gi > 0 && <View style={styles.divider} />}
          {[{ key: "", label: g.allLabel }, ...g.options].map((o) => (
            <Pressable key={o.key || "all"} testID={`${g.prefix}-${o.key || "all"}`} onPress={() => g.onChange(o.key)} hitSlop={{ top: 4, bottom: 4 }}
              style={[styles.chip, g.value === o.key && styles.chipOn]}>
              <Text style={[styles.chipText, g.value === o.key && styles.chipTextOn]}>{o.label}</Text>
            </Pressable>
          ))}
        </React.Fragment>
      ))}
    </ScrollView>
  );
}

// Whole exercise library: loaded once, then searched and filtered on the phone.
export default function ExerciseLibrary() {
  const styles = useStyles();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { call } = useApi();
  const [lib, setLib] = useState<Library | null>(null);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [group, setGroup] = useState("");
  const [level, setLevel] = useState("");
  const [equipment, setEquipment] = useState("");

  const load = useCallback(async () => {
    try {
      setError("");
      setLib(await call<Library>("/library"));
    } catch (e: any) {
      setError(e.message);
    }
  }, [call]);
  useEffect(() => { load(); }, [load]);

  const shown = useMemo(() => {
    if (!lib) return [];
    const q = query.trim().toLowerCase();
    return lib.items.filter((i) => (!group || i.group === group) && (!level || i.level === level)
      && (!equipment || i.equipment === equipment) && (!q || i.name.toLowerCase().includes(q) || i.target.toLowerCase().includes(q)));
  }, [lib, query, group, level, equipment]);

  if (!lib) {
    return (
      <View style={styles.center}>
        {error ? <><Text style={styles.err} testID="library-error">{error}</Text><PrimaryButton testID="library-retry-button" label="Retry" onPress={load} /></>
          : <ActivityIndicator color={colors.brandPrimary} size="large" />}
      </View>
    );
  }

  const renderItem = ({ item, index }: { item: LibraryItem; index: number }) => (
    <Pressable testID={`library-item-${index}`} onPress={() => router.push({ pathname: "/exercise/[id]", params: { id: item.id } })} style={styles.row}>
      <ExerciseThumb uri={item.thumb} size={64} />
      <View style={styles.rowText}>
        <Text style={styles.name} numberOfLines={2}>{item.name}</Text>
        <View style={styles.metaRow}>
          <LevelChip level={item.level} />
          <Text style={styles.meta} numberOfLines={1}>{item.target} · {item.equipment}</Text>
        </View>
      </View>
      <Ionicons name="chevron-forward" size={18} color={colors.muted} />
    </Pressable>
  );

  return (
    <View style={styles.root} testID="library-view">
      <View style={styles.filters}>
        <View style={styles.search}>
          <Ionicons name="search" size={18} color={colors.muted} />
          <TextInput testID="library-search-input" value={query} onChangeText={setQuery} placeholder="Search exercises"
            placeholderTextColor={colors.muted} style={styles.searchInput} autoCorrect={false} returnKeyType="search" />
          {!!query && <Pressable testID="library-search-clear" onPress={() => setQuery("")} hitSlop={8}><Ionicons name="close-circle" size={18} color={colors.muted} /></Pressable>}
        </View>
        <Chips groups={[{ prefix: "library-group", allLabel: "All muscles", value: group, onChange: setGroup, options: lib.groups.map((g) => ({ key: g, label: g })) }]} />
        <Chips groups={[
          { prefix: "library-level", allLabel: "Any level", value: level, onChange: setLevel, options: LEVELS },
          { prefix: "library-equipment", allLabel: "Any gear", value: equipment, onChange: setEquipment, options: lib.equipment.map((g) => ({ key: g, label: g })) },
        ]} />
        <Text style={styles.count} testID="library-count">
          {[`${shown.length} exercises`, group, LEVELS.find((l) => l.key === level)?.label, equipment].filter(Boolean).join(" · ")}
        </Text>
      </View>
      <FlashList
        data={shown}
        keyExtractor={(i) => i.id}
        renderItem={renderItem}
        keyboardShouldPersistTaps="handled"
        keyboardDismissMode="on-drag"
        contentContainerStyle={{ paddingHorizontal: spacing.xl, paddingBottom: (usesNativeTabs ? insets.bottom : 0) + spacing["2xl"] }}
        ItemSeparatorComponent={() => <View style={{ height: spacing.sm }} />}
        ListEmptyComponent={<Text style={styles.empty}>No exercises match. Try fewer filters.</Text>}
        ListFooterComponent={<Text style={styles.credit}>Demos by WorkoutX</Text>}
      />
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  root: { flex: 1 },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: spacing.lg, padding: spacing.xl },
  err: { color: c.error, fontWeight: "600", textAlign: "center" },
  filters: { gap: spacing.sm, paddingBottom: spacing.sm },
  search: { flexDirection: "row", alignItems: "center", gap: spacing.sm, marginHorizontal: spacing.xl, backgroundColor: c.surfaceSecondary, borderRadius: radius.md, paddingHorizontal: spacing.md, height: 48, borderWidth: 1, borderColor: c.border },
  searchInput: { flex: 1, fontSize: 16, fontWeight: "600", color: c.onSurface, height: 48 },
  chipRow: { paddingHorizontal: spacing.xl, gap: spacing.sm, alignItems: "center" },
  divider: { width: 1, height: 24, backgroundColor: c.borderStrong, marginHorizontal: spacing.xs },
  chip: { height: 36, paddingHorizontal: spacing.md, borderRadius: radius.pill, backgroundColor: c.surfaceSecondary, justifyContent: "center", borderWidth: 1, borderColor: c.border },
  chipOn: { backgroundColor: c.surfaceInverse, borderColor: c.surfaceInverse },
  chipText: { fontSize: 13, fontWeight: "800", color: c.onSurface, textTransform: "capitalize" },
  chipTextOn: { color: c.onSurfaceInverse },
  count: { paddingHorizontal: spacing.xl, fontSize: 12, fontWeight: "800", color: c.muted },
  row: { flexDirection: "row", alignItems: "center", gap: spacing.md, backgroundColor: c.surfaceSecondary, borderRadius: radius.lg, padding: spacing.sm },
  rowText: { flex: 1, gap: 4 },
  name: { fontSize: 15, fontWeight: "800", color: c.onSurface },
  metaRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  meta: { flex: 1, fontSize: 12, fontWeight: "700", color: c.muted, textTransform: "capitalize" },
  empty: { textAlign: "center", color: c.muted, fontWeight: "600", marginTop: spacing.xl },
  credit: { textAlign: "center", color: c.muted, fontSize: 12, fontWeight: "700", marginTop: spacing.lg },
}));
