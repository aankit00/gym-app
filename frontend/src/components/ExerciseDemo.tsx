import React, { useEffect, useState } from "react";
import { Text, View } from "react-native";
import { Image } from "expo-image";
import { useEvent } from "expo";
import { useIsFocused } from "expo-router";
import { useVideoPlayer, VideoView } from "expo-video";
import Animated, { useAnimatedStyle, useSharedValue, withDelay, withRepeat, withSequence, withTiming } from "react-native-reanimated";
import { makeStyles, radius, spacing } from "@/src/theme";

// Muted looping WorkoutX clip. Plays only while its screen is focused; reports errors so the caller can fall back.
function VideoDemo({ uri, poster, onError }: { uri: string; poster: string | null; onError: () => void }) {
  const styles = useStyles();
  const focused = useIsFocused();
  const player = useVideoPlayer(uri, (p) => {
    p.loop = true;
    p.muted = true;
  });
  const { status } = useEvent(player, "statusChange", { status: player.status });
  useEffect(() => { if (status === "error") onError(); }, [status, onError]);
  // a refused link (e.g. WorkoutX pausing media) can hang in "loading" instead of erroring
  useEffect(() => {
    if (status === "readyToPlay") return;
    const t = setTimeout(onError, 10000);
    return () => clearTimeout(t);
  }, [status, onError]);
  // web: there is no <video> during setup, so (re)start once mounted and whenever the screen regains focus
  useEffect(() => { if (focused) player.play(); else player.pause(); }, [focused, player]);
  return (
    <View style={[styles.frame, styles.video]} testID="exercise-demo-video">
      {poster && status !== "readyToPlay" && <Image source={{ uri: poster }} style={styles.fill} contentFit="contain" onError={() => {}} />}
      <VideoView player={player} style={styles.fill} contentFit="contain" nativeControls={false} />
    </View>
  );
}

// Start and finish photos cross-faded on a loop (fallback when no video is available).
function PhotoLoop({ images }: { images: string[] }) {
  const styles = useStyles();
  const top = useSharedValue(0);
  useEffect(() => {
    top.value = withRepeat(withSequence(
      withDelay(700, withTiming(1, { duration: 350 })),
      withDelay(700, withTiming(0, { duration: 350 })),
    ), -1);
  }, [top]);
  const fade = useAnimatedStyle(() => ({ opacity: top.value }));
  return (
    <View style={[styles.frame, styles.photo]} testID="exercise-demo-photos">
      <Image source={{ uri: images[0] }} style={styles.fill} contentFit="cover" />
      {images[1] && (
        <Animated.View style={[styles.fill, fade]}>
          <Image source={{ uri: images[1] }} style={styles.fill} contentFit="cover" />
        </Animated.View>
      )}
      <View style={styles.badge}><Text style={styles.badgeText}>START · FINISH</Text></View>
    </View>
  );
}

export default function ExerciseDemo({ video, poster, images }: { video: string | null; poster: string | null; images: string[] }) {
  const styles = useStyles();
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [video]);
  const onError = React.useCallback(() => setFailed(true), []);
  if (video && !failed) return <VideoDemo key={video} uri={video} poster={poster} onError={onError} />;
  if (images.length) return <PhotoLoop images={images} />;
  return (
    <View style={[styles.frame, styles.video, styles.none]} testID="exercise-demo-none">
      <Text style={styles.noneText}>Demo unavailable right now</Text>
    </View>
  );
}

const useStyles = makeStyles((c) => ({
  frame: { width: "100%", borderRadius: radius.lg, overflow: "hidden", backgroundColor: c.surfaceSecondary },
  video: { aspectRatio: 1 },
  photo: { aspectRatio: 3 / 2 },
  // explicit size: on web expo-video passes this style straight to <video>, which ignores left/right stretch
  fill: { position: "absolute", top: 0, left: 0, right: 0, bottom: 0, width: "100%", height: "100%" },
  badge: { position: "absolute", left: spacing.md, bottom: spacing.md, backgroundColor: c.scrim, paddingHorizontal: spacing.sm, paddingVertical: 4, borderRadius: radius.sm },
  badgeText: { color: c.onSurfaceInverse, fontSize: 11, fontWeight: "900", letterSpacing: 1 },
  none: { alignItems: "center", justifyContent: "center" },
  noneText: { color: c.muted, fontWeight: "700" },
}));
