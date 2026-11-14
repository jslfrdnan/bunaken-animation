import React from "react";
import { AbsoluteFill, Easing, Sequence, interpolate, useCurrentFrame } from "remotion";
import { Grain, ShotPlate, Vignette } from "./components/ShotPlate";
import { Subtitles } from "./components/Subtitles";
import { TitleCard } from "./components/Overlays";
import { PALETTE, SERIF } from "./theme";
import { FILM_FRAMES, SCENES } from "./film";

const LEAD = 6;

/** Kartu tagline di atas hitam — hanya sekali, di shot terakhir Scene 4. */
const TaglineCard: React.FC<{ text: string; fadeIn: number; hold: number }> = ({
  text,
  fadeIn,
  hold,
}) => {
  const frame = useCurrentFrame();
  const enter = interpolate(frame, [Math.max(1, fadeIn - 10), fadeIn + 12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const exit = interpolate(frame, [fadeIn + hold - 16, fadeIn + hold], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.in(Easing.cubic),
  });
  return (
    <AbsoluteFill style={{ backgroundColor: PALETTE.ink }}>
      <AbsoluteFill
        style={{ justifyContent: "center", alignItems: "center", opacity: enter * (1 - exit) }}
      >
        <div
          style={{
            fontFamily: SERIF,
            fontSize: 74,
            lineHeight: 1.28,
            textAlign: "center",
            color: PALETTE.cream,
            letterSpacing: "0.01em",
            maxWidth: 1320,
            textShadow: "0 4px 30px rgba(0,0,0,0.6)",
          }}
        >
          {text}
        </div>
        <div
          style={{
            width: 120,
            height: 1,
            marginTop: 44,
            backgroundColor: PALETTE.coral,
            opacity: 0.85,
          }}
        />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const EndFade: React.FC = () => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [12, 30], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return <AbsoluteFill style={{ backgroundColor: PALETTE.ink, opacity }} />;
};

/**
 * Animatic film penuh — 4 scene, 2:25, 3480 frame @ 24 fps.
 *
 * Plate masih papan cerita (belum render 3D), subtitle sudah mengikuti naskah
 * `docs/narasi.md`. Ini yang bisa diputar sementara Blender menyusul.
 */
export const FilmAnimatic: React.FC<{ slate?: boolean }> = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: PALETTE.ink }}>
      {SCENES.map((scene) =>
        scene.shots.map((shot, index) => {
          const absolute = scene.start + shot.start;
          const from = Math.max(0, absolute - LEAD);
          const lead = absolute - from;
          const isLastShot = scene.id === "scene-4" && index === scene.shots.length - 1;
          const tail = isLastShot ? 0 : LEAD;

          return (
            <Sequence
              key={shot.id}
              from={from}
              durationInFrames={lead + shot.duration + tail}
              name={`${scene.id}-shot-${shot.id}`}
            >
              {shot.card ? (
                <TaglineCard text={shot.card} fadeIn={lead} hold={shot.duration} />
              ) : (
                <ShotPlate shot={shot} lead={lead} tail={tail} />
              )}
            </Sequence>
          );
        }),
      )}

      <Sequence from={0} durationInFrames={72} name="judul">
        <TitleCard subtitle="Animasi 3D · 2 menit 25 detik" />
      </Sequence>

      <Subtitles />
      <Vignette />
      <Grain />

      <Sequence from={FILM_FRAMES - 30} durationInFrames={30} name="cut-to-black">
        <EndFade />
      </Sequence>
    </AbsoluteFill>
  );
};
