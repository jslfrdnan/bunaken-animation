import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { MONO, PALETTE, SAFE, SERIF } from "../theme";
import { SHOTS } from "../shots";

/** Judul film: overlay 3 detik pertama shot 010 (PROJECT.md §1.6). */
export const TitleCard: React.FC<{ subtitle?: string }> = ({
  subtitle = "Scene 1 · Permata",
}) => {
  const frame = useCurrentFrame();

  const enter = interpolate(frame, [4, 22], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const exit = interpolate(frame, [56, 70], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.in(Easing.cubic),
  });
  const alpha = enter * (1 - exit);
  const rise = (1 - enter) * 18 - exit * 10;

  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        paddingBottom: 90,
        opacity: alpha,
        transform: `translateY(${rise}px)`,
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "radial-gradient(50% 42% at 50% 52%, rgba(6,24,28,0.55), transparent 72%)",
        }}
      />
      <div style={{ position: "relative", display: "flex", flexDirection: "column", alignItems: "center" }}>
        <div
          style={{
            fontFamily: MONO,
            fontSize: 20,
            letterSpacing: "0.52em",
            textTransform: "uppercase",
            color: PALETTE.cream,
            opacity: 0.72,
            marginBottom: 26,
            paddingLeft: "0.52em",
          }}
        >
          Sebuah animasi 3D
        </div>
        <div
          style={{
            width: 96,
            height: 1,
            backgroundColor: PALETTE.coral,
            opacity: 0.8,
            marginBottom: 30,
          }}
        />
        <h1
          style={{
            margin: 0,
            fontFamily: SERIF,
            fontWeight: 400,
            fontSize: 112,
            letterSpacing: "0.075em",
            color: PALETTE.cream,
            textShadow: "0 6px 38px rgba(6,24,28,0.65)",
            paddingLeft: "0.075em",
          }}
        >
          WARISAN BUNAKEN
        </h1>
        <div
          style={{
            marginTop: 30,
            fontFamily: MONO,
            fontSize: 17,
            letterSpacing: "0.34em",
            textTransform: "uppercase",
            color: PALETTE.sand,
            opacity: 0.75,
            paddingLeft: "0.34em",
          }}
        >
          {subtitle}
        </div>
      </div>
    </AbsoluteFill>
  );
};
export const Slate: React.FC<{ showDetails: boolean; label?: string }> = ({
  showDetails,
  label = "ANIMATIC v001",
}) => {
  const frame = useCurrentFrame();
  const shot = SHOTS.find((s) => frame >= s.start && frame < s.start + s.duration) ?? SHOTS[SHOTS.length - 1];
  const local = frame - shot.start;
  const fade = interpolate(local, [0, 8], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ opacity: fade * 0.94 }}>
      <div
        style={{
          position: "absolute",
          left: SAFE.x,
          bottom: SAFE.bottom,
          display: "flex",
          alignItems: "center",
          gap: 14,
        }}
      >
        <div style={{ width: 9, height: 9, backgroundColor: PALETTE.coral }} />
        <div
          style={{
            fontFamily: MONO,
            fontSize: 19,
            letterSpacing: "0.18em",
            color: PALETTE.cream,
          }}
        >
          SHOT {shot.id} · {shot.duration / 24} s
        </div>
      </div>

      {showDetails && (
        <div
          style={{
            position: "absolute",
            left: SAFE.x + 23,
            bottom: SAFE.bottom - 30,
            fontFamily: MONO,
            fontSize: 15,
            letterSpacing: "0.06em",
            color: PALETTE.cream,
            opacity: 0.6,
            display: "flex",
            gap: 10,
          }}
        >
          <span>{shot.asset}</span>
          <span style={{ opacity: 0.5 }}>/</span>
          <span>{shot.camera}</span>
        </div>
      )}

      <div
        style={{
          position: "absolute",
          right: SAFE.x,
          bottom: SAFE.bottom + 4,
          fontFamily: MONO,
          fontSize: 15,
          letterSpacing: "0.22em",
          color: PALETTE.cream,
          opacity: 0.55,
          textAlign: "right",
        }}
      >
        SCENE 1 · {label}
        <div style={{ marginTop: 8, opacity: 0.7 }}>35 s · 24 fps</div>
      </div>
    </AbsoluteFill>
  );
};
