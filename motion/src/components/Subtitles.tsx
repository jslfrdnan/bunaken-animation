import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { MONO, PALETTE, SAFE } from "../theme";
import { CUES, FPS } from "../subtitles";

/**
 * Subtitle bakar (burned-in) untuk animatic.
 *
 * Aturan PROJECT.md §3: putih dengan outline hitam tipis, maksimal 2 baris,
 * tidak menimpa wajah — diletakkan di bawah area aman, bukan tengah frame.
 * Fade 6 frame masuk/keluar supaya tidak berkedip.
 */
export const Subtitles: React.FC = () => {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  const cue = CUES.find((c) => t >= c.start && t < c.end);

  if (!cue) return null;

  const local = t - cue.start;
  const remaining = cue.end - t;
  const opacity = interpolate(
    Math.min(local, remaining),
    [0, 0.25],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  return (
    <AbsoluteFill style={{ opacity, justifyContent: "flex-end", alignItems: "center" }}>
      <div
        style={{
          marginBottom: SAFE.bottom + 34,
          maxWidth: 1180,
          textAlign: "center",
          fontFamily: MONO,
          fontSize: 40,
          lineHeight: 1.32,
          letterSpacing: "0.01em",
          color: PALETTE.cream,
          textShadow:
            "0 2px 6px rgba(0,0,0,0.95), 0 0 2px rgba(0,0,0,1), 0 0 14px rgba(0,0,0,0.55)",
          padding: "0 28px",
        }}
      >
        {cue.lines.map((line, i) => (
          <div key={i}>{line}</div>
        ))}
      </div>
    </AbsoluteFill>
  );
};
