import React from "react";
import { Platform } from "react-native";
import { Tabs } from "expo-router";
import { NativeTabs } from "expo-router/unstable-native-tabs";
import { Ionicons } from "@react-native-vector-icons/ionicons";
import { usesNativeTabs } from "@/src/navigation";
import { useTheme } from "@/src/theme";

const TABS = [
  { name: "home", label: "Home", sf: "house.fill", icon: "home" },
  { name: "board", label: "Board", sf: "trophy.fill", icon: "trophy" },
  { name: "stats", label: "Stats", sf: "chart.bar.fill", icon: "stats-chart" },
  { name: "me", label: "Me", sf: "person.fill", icon: "person" },
] as const;

export default function TabsLayout() {
  const { colors } = useTheme();
  if (usesNativeTabs) {
    return (
      <NativeTabs tintColor={colors.onSurface}>
        {TABS.map((t) => (
          <NativeTabs.Trigger key={t.name} name={t.name}>
            <NativeTabs.Trigger.Icon sf={t.sf as any} />
            <NativeTabs.Trigger.Label>{t.label}</NativeTabs.Trigger.Label>
          </NativeTabs.Trigger>
        ))}
      </NativeTabs>
    );
  }
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.onSurface,
        tabBarInactiveTintColor: colors.muted,
        tabBarStyle: { backgroundColor: colors.surfaceSecondary, borderTopColor: colors.border, ...(Platform.OS === "web" ? { height: 64 } : {}) },
        tabBarItemStyle: { alignSelf: "center" },
        tabBarLabelStyle: { fontWeight: "700", fontSize: 12 },
      }}
    >
      {TABS.map((t) => (
        <Tabs.Screen key={t.name} name={t.name} options={{
          title: t.label,
          tabBarButtonTestID: `tab-${t.name}`,
          tabBarIcon: ({ color, focused }) => <Ionicons name={(focused ? t.icon : `${t.icon}-outline`) as any} size={24} color={color} />,
        }} />
      ))}
    </Tabs>
  );
}
