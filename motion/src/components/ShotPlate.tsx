import React from "react";
import { AbsoluteFill, Easing, Img, interpolate, staticFile, useCurrentFrame } from "remotion";
import { PALETTE } from "../theme";
import type { Grade, Shot } from "../shots";

const GRADE: Record<Grade, { tint: string; strength: number; filter: string }> = {
  golden: { tint: PALETTE.sand, strength: 0.34, filter: "contrast(1.03) saturate(1.05)" },
  shallow: { tint: PALETTE.teal, strength: 0.4, filter: "contrast(1.02) saturate(1.05)" },
  reef: { tint: PALETTE.deepTeal, strength: 0.36, filter: "contrast(1.05) saturate(1.08)" },
  deep: { tint: PALETTE.deepTeal, strength: 0.5, filter: "contrast(1.1) saturate(1.05) brightness(0.94)" },
  deck: { tint: PALETTE.sand, strength: 0.22, filter: "contrast(1.02) saturate(1.02)" },
  warm: { tint: PALETTE.sand, strength: 0.16, filter: "contrast(1.03) saturate(1.04)" },
};

/** Kartu cahaya bawah air: tiga berkas lebar yang bergeser sangat pelan. */
const WaterLight: React.FC<{ frame: number; strength: number }> = ({ frame, strength }) => {
  const drift = Math.sin(frame / 90) * 3;
  return (
    <AbsoluteFill
      style={{
        opacity: strength,
        mixBlendMode: "screen",
        transform: `rotate(-12deg) scale(1.4) translateX(${drift}%)`,
        background: `linear-gradient(100deg,
          transparent 12%,
          rgba(242,233,220,0.30) 16%,
          transparent 21%,
          transparent 34%,
          rgba(242,233,220,0.18) 38%,
          transparent 45%,
          transparent 58%,
          rgba(242,233,220,0.24) 62%,
          transparent 68%)`,
        filter: "blur(16px)",
      }}
    />
  );
};

export const ShotPlate: React.FC<{ shot: Shot; lead: number; tail: number }> = ({
  shot,
  lead,
  tail,
}) => {
  const frame = useCurrentFrame();

  const p = interpolate(frame, [lead, lead + shot.duration], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.42, 0, 0.28, 1),
  });

  const scale = shot.from.scale + (shot.to.scale - shot.from.scale) * p;
  const x = shot.from.x + (shot.to.x - shot.from.x) * p;
  const y = shot.from.y + (shot.to.y - shot.from.y) * p;

  const shakeX = shot.shake ? Math.sin(frame * 0.62) * 4 + Math.sin(frame * 1.7) * 1.6 : 0;
  const shakeY = shot.shake ? Math.cos(frame * 0.51) * 3 : 0;
  const shakeR = shot.shake ? Math.sin(frame * 0.33) * 0.16 : 0;

  // Shot pertama tidak boleh mulai dari hitam: langsung penuh sejak frame 0.
  // fadeOut minimal 1 frame supaya inputRange tetap naik ketat saat tail = 0
  // (shot terakhir tidak punya cross-dissolve keluar).
  const fadeOut = Math.max(tail, 1);
  const opacity = interpolate(
    frame,
    [0, Math.max(lead, 1), lead + shot.duration, lead + shot.duration + fadeOut],
    [lead > 0 ? 0 : 1, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  const g = GRADE[shot.grade];

  return (
    <AbsoluteFill style={{ opacity, backgroundColor: PALETTE.ink }}>
      <AbsoluteFill style={{ transform: `translate(${shakeX}px, ${shakeY}px) rotate(${shakeR}deg) scale(1.02)` }}>
        <Img
          src={staticFile(shot.src)}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            objectPosition: `${x}% ${y}%`,
            transform: `scale(${scale})`,
            filter: g.filter,
          }}
        />
        {/* pewarnaan: papan cerita abu-abu diberi tint palette */}
        <AbsoluteFill style={{ backgroundColor: g.tint, opacity: g.strength, mixBlendMode: "color" }} />
        {/* cahaya hangat dari atas untuk shot permukaan */}
        {(shot.grade === "golden" || shot.grade === "warm" || shot.grade === "deck") && (
          <AbsoluteFill
            style={{
              background: `radial-gradient(120% 80% at 78% -10%, rgba(232,213,176,0.45), transparent 60%)`,
              mixBlendMode: "soft-light",
            }}
          />
        )}
        {(shot.grade === "reef" || shot.grade === "deep") && (
          <WaterLight frame={frame} strength={shot.grade === "deep" ? 0.85 : 0.6} />
        )}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

export const Vignette: React.FC = () => (
  <AbsoluteFill
    style={{
      background:
        "radial-gradient(78% 68% at 50% 48%, transparent 42%, rgba(6,24,28,0.42) 82%, rgba(6,24,28,0.78) 100%)",
    }}
  />
);

const NOISE =
  "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='160' height='160' filter='url(%23n)' opacity='0.5'/%3E%3C/svg%3E\")";

/** Grain halus supaya gambar diam tidak terasa seperti slide presentasi. */
export const Grain: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill
      style={{
        backgroundImage: NOISE,
        backgroundPosition: `${(frame * 37) % 160}px ${(frame * 53) % 160}px`,
        opacity: 0.07,
        mixBlendMode: "overlay",
      }}
    />
  );
};
