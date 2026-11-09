import React, { useLayoutEffect } from "react";
import { AbsoluteFill, Sequence, interpolate, useCurrentFrame } from "remotion";
import { ThreeCanvas } from "@remotion/three";
import { useThree } from "@react-three/fiber";
import { Grain, Vignette } from "./components/ShotPlate";
import { Slate, TitleCard } from "./components/Overlays";
import { PALETTE } from "./theme";
import { TOTAL_FRAMES } from "./shots";
import { SHOTS_3D } from "./three/shots3d";
import { ShotCameraRig, SkyDome } from "./three/Camera";
import { World } from "./three/World";
import { useAssets } from "./three/Assets";

/** Memaksa three menggambar ulang setelah GLB selesai dimuat (frameloop 'never'). */
const AdvanceOnReady: React.FC<{ ready: boolean }> = ({ ready }) => {
  const advance = useThree((state) => state.advance);
  useLayoutEffect(() => {
    if (!ready) {
      return;
    }
    advance(performance.now());
  }, [ready, advance]);
  return null;
};



export type Scene1ThreeDProps = {
  slate: boolean;
};

/** Cahaya bawah air: berkas lebar yang bergeser pelan, plus partikel halus. */
const UnderwaterGrade: React.FC<{ frame: number }> = ({ frame }) => {
  const drift = Math.sin(frame / 70) * 4;
  return (
    <>
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(63,194,192,0.18) 0%, rgba(15,92,99,0.30) 45%, rgba(6,58,68,0.52) 100%)",
          mixBlendMode: "multiply",
        }}
      />
      <AbsoluteFill
        style={{
          opacity: 0.55,
          mixBlendMode: "screen",
          transform: `rotate(-14deg) scale(1.5) translateX(${drift}%)`,
          background: `linear-gradient(102deg,
            transparent 10%,
            rgba(223,243,234,0.22) 15%,
            transparent 20%,
            transparent 33%,
            rgba(223,243,234,0.15) 38%,
            transparent 44%,
            transparent 57%,
            rgba(223,243,234,0.18) 62%,
            transparent 68%)`,
          filter: "blur(18px)",
        }}
      />
    </>
  );
};

const AboveWaterGrade: React.FC = () => (
  <AbsoluteFill
    style={{
      background:
        "linear-gradient(180deg, rgba(255,226,181,0.18) 0%, transparent 38%, rgba(11,78,92,0.28) 100%)",
      mixBlendMode: "soft-light",
    }}
  />
);

const EndFade: React.FC = () => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [TOTAL_FRAMES - 22, TOTAL_FRAMES - 1], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return <AbsoluteFill style={{ backgroundColor: PALETTE.ink, opacity }} />;
};

/**
 * Scene 1 versi 3D — 35 detik @ 24 fps.
 *
 * Seluruh gambar dihasilkan real-time di Remotion dari aset Blender yang
 * sudah ada (`motion/public/models/*.glb`). Blender hanya dipakai untuk
 * membuat aset, bukan untuk merender video.
 */
export const Scene1ThreeD: React.FC<Scene1ThreeDProps> = ({ slate }) => {
  const frame = useCurrentFrame();
  const ready = useAssets();

  const shot =
    SHOTS_3D.find((candidate) => frame >= candidate.start && frame < candidate.start + candidate.duration) ??
    SHOTS_3D[SHOTS_3D.length - 1];

  return (
    <AbsoluteFill style={{ backgroundColor: PALETTE.ink }}>
      <ThreeCanvas
        width={1920}
        height={1080}
        flat
        gl={{ antialias: true, alpha: false }}
        camera={{ fov: shot.fov, near: 0.05, far: 30000, position: [0, 5, 30] }}
      >
        <color attach="background" args={[shot.underwater ? "#12545F" : "#CBDDE4"]} />
        <fog
          attach="fog"
          args={
            shot.underwater
              ? ["#1B6F7B", 3, 62]
              : ["#DCE9EA", 350, 7200]
          }
        />
        {!shot.underwater && <SkyDome />}
        <ShotCameraRig />
        <World ready={ready} shot={shot} frame={frame} />
        <AdvanceOnReady ready={ready} />
      </ThreeCanvas>

      {shot.underwater ? <UnderwaterGrade frame={frame} /> : <AboveWaterGrade />}

      <Vignette />
      <Grain />

      <Sequence from={0} durationInFrames={72} name="judul">
        <TitleCard />
      </Sequence>

      {slate && <Slate showDetails label="3D PREVIZ v001" />}

      <Sequence from={TOTAL_FRAMES - 22} durationInFrames={22} name="cut-to-black">
        <EndFade />
      </Sequence>
    </AbsoluteFill>
  );
};
