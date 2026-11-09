import React from "react";
import { AbsoluteFill, Sequence, interpolate, useCurrentFrame } from "remotion";
import { ShotPlate, Vignette, Grain } from "./components/ShotPlate";
import { Slate, TitleCard } from "./components/Overlays";
import { PALETTE } from "./theme";
import { SHOTS, TOTAL_FRAMES } from "./shots";

export type Scene1AnimaticProps = {
  slate: boolean;
};

const LEAD = 6;

const EndFade: React.FC = () => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [TOTAL_FRAMES - 18, TOTAL_FRAMES - 1], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return <AbsoluteFill style={{ backgroundColor: PALETTE.ink, opacity }} />;
};

/**
 * Animatic Scene 1 — 35 detik.
 *
 * Dibuat dari aset yang sudah ada: papan cerita v002 + tiga foto acuan.
 * Belum ada render 3D, rig Nara, atau audio; animatic ini yang jadi acuan
 * timing untuk Blender nanti.
 */
export const Scene1Animatic: React.FC<Scene1AnimaticProps> = ({ slate }) => {
  return (
    <AbsoluteFill style={{ backgroundColor: PALETTE.ink }}>
      {SHOTS.map((shot, index) => {
        const from = Math.max(0, shot.start - LEAD);
        const lead = shot.start - from;
        const tail = index === SHOTS.length - 1 ? 0 : LEAD;
        return (
          <Sequence
            key={shot.id}
            from={from}
            durationInFrames={lead + shot.duration + tail}
            name={`shot-${shot.id}`}
          >
            <ShotPlate shot={shot} lead={lead} tail={tail} />
          </Sequence>
        );
      })}

      <Sequence from={0} durationInFrames={72} name="judul">
        <TitleCard />
      </Sequence>

      <Vignette />
      <Grain />

      {slate && <Slate showDetails />}

      <Sequence from={TOTAL_FRAMES - 18} durationInFrames={18} name="cut-to-black">
        <EndFade />
      </Sequence>
    </AbsoluteFill>
  );
};
