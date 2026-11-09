import React, { useLayoutEffect, useMemo } from "react";
import { useCurrentFrame } from "remotion";
import { useThree } from "@react-three/fiber";
import * as THREE from "three";
import { SHOTS_3D } from "./shots3d";

const smooth = (t: number) => t * t * (3 - 2 * t);
const clamp01 = (v: number) => Math.max(0, Math.min(1, v));
const lerp3 = (
  a: [number, number, number],
  b: [number, number, number],
  t: number,
): [number, number, number] => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];

/** Kamera mengikuti shot yang sedang berjalan; tiap shot punya gerak sendiri. */
export const ShotCameraRig: React.FC = () => {
  const frame = useCurrentFrame();
  const camera = useThree((s) => s.camera) as THREE.PerspectiveCamera;

  const shot = SHOTS_3D.find((s) => frame >= s.start && frame < s.start + s.duration) ?? SHOTS_3D[SHOTS_3D.length - 1];

  useLayoutEffect(() => {
    const p = smooth(clamp01((frame - shot.start) / shot.duration));
    const shakeX = shot.shake ? Math.sin(frame * 0.9) * 0.06 : 0;
    const shakeY = shot.shake ? Math.cos(frame * 0.7) * 0.05 : 0;

    const pos = lerp3(shot.posFrom, shot.posTo, p);
    const look = lerp3(shot.lookFrom, shot.lookTo, p);

    camera.position.set(pos[0] + shakeX, pos[1] + shakeY, pos[2]);
    camera.fov = shot.fov;
    camera.near = 0.05;
    camera.far = 30000;
    camera.lookAt(look[0], look[1], look[2]);
    camera.updateProjectionMatrix();
  }, [frame, shot, camera]);

  return null;
};

/** Langit: gradien krem di horizon ke biru kelabu di atas. */
export const SkyDome: React.FC = () => {
  const material = useMemo(
    () =>
      new THREE.ShaderMaterial({
        side: THREE.BackSide,
        depthWrite: false,
        uniforms: {
          top: { value: new THREE.Color("#7FA6BA") },
          horizon: { value: new THREE.Color("#F3DDB6") },
        },
        vertexShader: `
          varying vec3 vWorld;
          void main() {
            vWorld = (modelMatrix * vec4(position, 1.0)).xyz;
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          }
        `,
        fragmentShader: `
          uniform vec3 top;
          uniform vec3 horizon;
          varying vec3 vWorld;
          void main() {
            float h = normalize(vWorld).y;
            float t = smoothstep(-0.02, 0.55, h);
            gl_FragColor = vec4(mix(horizon, top, t), 1.0);
          }
        `,
      }),
    [],
  );
  return (
    <mesh material={material} scale={[-1, 1, 1]}>
      <sphereGeometry args={[16000, 32, 16]} />
    </mesh>
  );
};

export const Water: React.FC<{ underwater: boolean }> = () => {
  return (
    <mesh rotation-x={-Math.PI / 2} position={[0, 0, 0]}>
      <planeGeometry args={[12000, 12000]} />
      <meshStandardMaterial
        color="#1FA3A3"
        roughness={0.22}
        metalness={0.08}
        transparent
        opacity={0.88}
        side={THREE.DoubleSide}
      />
    </mesh>
  );
};

/** Berkas cahaya bawah air: beberapa bidang aditif, cukup untuk animatic. */
export const GodRays: React.FC<{ frame: number }> = ({ frame }) => {
  const drift = Math.sin(frame / 80) * 0.6;
  return (
    <group position={[30, -4.4, 60]} rotation={[0, 0.35, 0]}>
      {[0, 1, 2, 3].map((i) => (
        <mesh key={i} position={[-4 + i * 3.4 + drift, 2.6, -2 + i * 0.9]} rotation={[0, 0, 0.18 + i * 0.02]}>
          <planeGeometry args={[1.1, 9]} />
          <meshBasicMaterial
            color="#DFF3EA"
            transparent
            opacity={0.1}
            blending={THREE.AdditiveBlending}
            depthWrite={false}
            side={THREE.DoubleSide}
          />
        </mesh>
      ))}
    </group>
  );
};
