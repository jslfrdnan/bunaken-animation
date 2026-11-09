import React, { useMemo } from "react";
import * as THREE from "three";
import { cloneAsset, getAsset, makeRig, makeRigExact } from "./Assets";
import { B, type Shot3D } from "./shots3d";

/**
 * Dunia Scene 1 dalam three.js.
 *
 * Semua posisi ditulis dalam koordinat Blender lewat `B()` supaya bisa
 * dibandingkan langsung dengan `scenes/scene-1.blend`.
 *   pantai  : blender y = 0   → three z = 0
 *   dermaga : blender y -104…0 → three z 0…104 (laut ada di +z)
 *   karang  : blender (35, -62, -5.6) → three (35, -5.6, 62)
 */

const REEF = B(35, -62, -5.6);
const SAND_Y = -6.2;
const BOAT_CENTER = B(18, -55, 0);
const BOAT_YAW = -0.22;
const PIER_Y = 1.26;

/** Pembangkit acak deterministik: hasil render harus sama di tiap frame. */
const rng = (seed: number) => () => {
  seed = (seed + 0x6d2b79f5) | 0;
  let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
  t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
};

/* ------------------------------------------------------------------ */
/* Air                                                                 */
/* ------------------------------------------------------------------ */

const WATER_VERT = /* glsl */ `
  uniform float uTime;
  varying vec3 vWorld;
  varying vec3 vNormalW;
  void main() {
    vec3 p = position;
    float h = sin(p.x * 0.055 + uTime * 0.45) * 0.22
            + sin(p.y * 0.041 - uTime * 0.37) * 0.30
            + sin((p.x + p.y) * 0.017 + uTime * 0.2) * 0.5;
    p.z += h;
    float dx = cos(p.x * 0.055 + uTime * 0.45) * 0.012
             + cos((p.x + p.y) * 0.017 + uTime * 0.2) * 0.0085;
    float dy = cos(p.y * 0.041 - uTime * 0.37) * 0.012
             + cos((p.x + p.y) * 0.017 + uTime * 0.2) * 0.0085;
    vec4 wp = modelMatrix * vec4(p, 1.0);
    vWorld = wp.xyz;
    vNormalW = normalize(normalMatrix * vec3(-dx, -dy, 1.0));
    gl_Position = projectionMatrix * viewMatrix * wp;
  }
`;

const WATER_FRAG = /* glsl */ `
  uniform vec3 uDeep;
  uniform vec3 uShallow;
  uniform vec3 uSun;
  uniform float uUnder;
  varying vec3 vWorld;
  varying vec3 vNormalW;
  void main() {
    vec3 N = normalize(vNormalW);
    if (uUnder > 0.5) N = -N;
    vec3 V = normalize(cameraPosition - vWorld);
    float fres = pow(1.0 - clamp(abs(dot(V, N)), 0.0, 1.0), 3.0);
    vec3 col = mix(uDeep, uShallow, fres);
    if (uUnder > 0.5) {
      col = mix(col, vec3(0.38, 0.80, 0.79), 0.35 + fres * 0.35);
    }
    vec3 H = normalize(V + normalize(uSun));
    float spec = pow(max(dot(N, H), 0.0), 140.0);
    col += spec * (uUnder > 0.5 ? 0.25 : 0.85);
    gl_FragColor = vec4(col, 1.0);
  }
`;

export const Ocean: React.FC<{ frame: number; underwater: boolean }> = ({ frame, underwater }) => {
  const material = useMemo(
    () =>
      new THREE.ShaderMaterial({
        vertexShader: WATER_VERT,
        fragmentShader: WATER_FRAG,
        side: THREE.DoubleSide,
        uniforms: {
          uTime: { value: 0 },
          uDeep: { value: new THREE.Color("#0B4E5C") },
          uShallow: { value: new THREE.Color("#3FC2C0") },
          uSun: { value: new THREE.Vector3(-0.45, 0.55, -0.7) },
          uUnder: { value: 0 },
        },
      }),
    [],
  );

  material.uniforms.uTime.value = frame / 24;
  material.uniforms.uUnder.value = underwater ? 1 : 0;

  return (
    <mesh rotation-x={-Math.PI / 2} material={material}>
      <planeGeometry args={[14000, 14000, 96, 96]} />
    </mesh>
  );
};

/* ------------------------------------------------------------------ */
/* Terumbu                                                             */
/* ------------------------------------------------------------------ */

/** Empat jenis karang dari `env-reef.glb`, masing-masing dijadikan satu unit. */
const CORAL_SPECIES: string[][] = [
  ["ENV_reef_boulder-coral"],
  ["ENV_reef_branching-coral"],
  ["ENV_reef_branching-coral_b"],
  ["ENV_reef_table-coral", "ENV_reef_table-coral_stem"],
];

type CoralTemplate = { rig: THREE.Group; base: number };

const useCoralTemplates = (ready: boolean): CoralTemplate[] =>
  useMemo(() => {
    if (!ready) {
      return [];
    }
    const source = getAsset("reef");
    if (!source) {
      return [];
    }
    source.updateMatrixWorld(true);
    const templates: CoralTemplate[] = [];
    for (const names of CORAL_SPECIES) {
      const rig = makeRigExact(source, names);
      if (!rig) {
        continue;
      }
      const box = new THREE.Box3().setFromObject(rig);
      templates.push({ rig, base: -box.min.y });
    }
    return templates;
  }, [ready]);

const CORAL_PLACEMENTS = (() => {
  const random = rng(11);
  // delapan gumpalan utama; sisanya menyebar mengisi celah
  const clusters: Array<[number, number]> = [
    [-4.6, 0.9],
    [-1.2, -1.4],
    [2.2, 0.6],
    [4.8, -0.7],
    [-3.4, -2.0],
    [1.4, 2.2],
    [5.2, 2.0],
    [-6.0, -0.4],
  ];
  return Array.from({ length: 120 }, (_, index) => {
    let x: number;
    let z: number;
    if (index < 84) {
      const [cx, cz] = clusters[index % clusters.length];
      const angle = random() * Math.PI * 2;
      const radius = Math.sqrt(random()) * 2.5;
      x = cx + Math.cos(angle) * radius;
      z = cz + Math.sin(angle) * radius * 0.65;
    } else {
      const angle = random() * Math.PI * 2;
      const radius = Math.sqrt(random());
      x = Math.cos(angle) * radius * 7.5;
      z = Math.sin(angle) * radius * 3.4;
    }
    x = Math.max(-7.2, Math.min(7.2, x));
    z = Math.max(-3.3, Math.min(3.3, z));
    const small = index % 3 !== 0;
    return {
      key: index,
      species: Math.floor(random() * CORAL_SPECIES.length),
      x,
      z,
      scale: small ? 0.35 + random() * 0.45 : 0.85 + random() * 0.45,
      rotation: random() * Math.PI * 2,
    };
  });
})();

const ReefField: React.FC<{ ready: boolean }> = ({ ready }) => {
  const templates = useCoralTemplates(ready);
  const instances = useMemo(() => {
    if (templates.length === 0) {
      return [];
    }
    return CORAL_PLACEMENTS.map((placement) => {
      const template = templates[placement.species % templates.length];
      return {
        ...placement,
        mesh: template.rig.clone(true),
        y: SAND_Y + template.base * placement.scale,
      };
    });
  }, [templates]);

  if (templates.length === 0) {
    return null;
  }

  return (
    <group>
      {instances.map((instance) => (
        <primitive
          key={instance.key}
          object={instance.mesh}
          position={[REEF[0] + instance.x, instance.y, REEF[2] + instance.z]}
          rotation={[0, instance.rotation, 0]}
          scale={instance.scale}
        />
      ))}
    </group>
  );
};

/* ------------------------------------------------------------------ */
/* Detail terumbu: sea fan, spons, bulu babi, plankton                 */
/* ------------------------------------------------------------------ */

/** Kipas laut: beberapa bilah tipis yang melebar dari satu titik. */
const FAN_GEOMETRY = (() => {
  const random = rng(23);
  const verts: number[] = [];
  const indices: number[] = [];
  const blades = 11;
  for (let i = 0; i < blades; i++) {
    const angle = -1.15 + (2.3 * i) / (blades - 1) + (random() - 0.5) * 0.06;
    const radius = 0.7 + random() * 0.55;
    const width = 0.08 + random() * 0.05;
    const base = verts.length / 3;
    verts.push(0, 0, 0);
    verts.push(Math.sin(angle - width) * radius, Math.cos(angle - width) * radius, 0);
    verts.push(Math.sin(angle + width) * radius, Math.cos(angle + width) * radius, 0);
    indices.push(base, base + 1, base + 2);
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(verts, 3));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
})();

const FANS = [
  { x: -6.2, z: 2.2, yaw: 0.4, scale: 0.6, color: "#6E5A7A" },
  { x: -4.0, z: -2.4, yaw: 1.2, scale: 0.5, color: "#8A6A5A" },
  { x: 2.8, z: 2.8, yaw: 2.1, scale: 0.55, color: "#6E5A7A" },
  { x: 5.8, z: -1.8, yaw: 0.8, scale: 0.65, color: "#7A5F6E" },
  { x: 6.8, z: 1.4, yaw: 2.7, scale: 0.45, color: "#8A6A5A" },
  { x: -1.2, z: -3.0, yaw: 3.2, scale: 0.55, color: "#6E5A7A" },
  { x: 1.0, z: 3.1, yaw: 1.6, scale: 0.5, color: "#7A5F6E" },
];

const SPONGES = [
  { x: -6.8, z: -0.8, yaw: 0.3, color: "#B06A48" },
  { x: 6.2, z: 2.2, yaw: 1.4, color: "#C08A55" },
  { x: 3.6, z: -2.6, yaw: 2.2, color: "#B06A48" },
  { x: -3.2, z: 2.6, yaw: 0.9, color: "#C08A55" },
  { x: 0.4, z: -2.8, yaw: 3.0, color: "#B06A48" },
];

// x, z, tinggi, radius
const TUBES: Array<[number, number, number, number]> = [
  [-0.14, 0.10, 0.34, 0.08],
  [0.08, 0.04, 0.44, 0.07],
  [0.05, -0.12, 0.28, 0.075],
  [-0.07, -0.09, 0.22, 0.06],
];

const URCHINS = [
  { x: -5.0, z: 1.9 },
  { x: -2.8, z: -2.8 },
  { x: 0.8, z: 1.5 },
  { x: 3.0, z: -1.2 },
  { x: 5.2, z: 2.6 },
  { x: -6.4, z: -2.2 },
  { x: 6.6, z: -1.0 },
  { x: 2.0, z: 2.8 },
];

const ReefProps: React.FC = () => (
  <group>
    {FANS.map((fan, index) => (
      <mesh
        key={`fan-${index}`}
        geometry={FAN_GEOMETRY}
        position={[REEF[0] + fan.x, SAND_Y, REEF[2] + fan.z]}
        rotation={[0, fan.yaw, 0]}
        scale={fan.scale}
      >
        <meshStandardMaterial color={fan.color} side={THREE.DoubleSide} roughness={0.75} />
      </mesh>
    ))}
    {SPONGES.map((sponge, index) => (
      <group
        key={`sponge-${index}`}
        position={[REEF[0] + sponge.x, SAND_Y, REEF[2] + sponge.z]}
        rotation={[0, sponge.yaw, 0]}
      >
        {TUBES.map((tube, tubeIndex) => (
          <mesh key={tubeIndex} position={[tube[0], tube[2] / 2, tube[1]]}>
            <cylinderGeometry args={[tube[3] * 0.75, tube[3], tube[2], 6]} />
            <meshStandardMaterial color={sponge.color} roughness={0.8} />
          </mesh>
        ))}
      </group>
    ))}
    {URCHINS.map((urchin, index) => (
      <mesh
        key={`urchin-${index}`}
        position={[REEF[0] + urchin.x, SAND_Y + 0.1, REEF[2] + urchin.z]}
        scale={0.11}
      >
        <icosahedronGeometry args={[1, 0]} />
        <meshStandardMaterial color="#24262C" roughness={0.6} flatShading />
      </mesh>
    ))}
  </group>
);

/** Partikel plankton, hanya muncul di shot bawah laut. */
const PLANKTON_POSITIONS = (() => {
  const random = rng(97);
  const positions = new Float32Array(700 * 3);
  for (let i = 0; i < 700; i++) {
    positions[i * 3] = (random() - 0.5) * 30;
    positions[i * 3 + 1] = (random() - 0.5) * 9;
    positions[i * 3 + 2] = (random() - 0.5) * 22;
  }
  return positions;
})();

const Plankton: React.FC<{ frame: number }> = ({ frame }) => {
  const geometry = useMemo(() => {
    const points = new THREE.BufferGeometry();
    points.setAttribute("position", new THREE.BufferAttribute(PLANKTON_POSITIONS, 3));
    return points;
  }, []);
  const time = frame / 24;

  return (
    <points
      geometry={geometry}
      position={[REEF[0], -2.6 + Math.sin(time * 0.18) * 0.35, REEF[2]]}
      rotation={[0, time * 0.012, 0]}
    >
      <pointsMaterial color="#CFEDE4" size={0.035} transparent opacity={0.42} depthWrite={false} />
    </points>
  );
};

/* ------------------------------------------------------------------ */
/* Ikan & penyu                                                        */
/* ------------------------------------------------------------------ */

type SchoolProps = {
  rig: THREE.Group | null;
  count: number;
  center: [number, number, number];
  radius: number;
  height: number;
  scale: number;
  speed: number;
  phase: number;
  frame: number;
  yawOffset?: number;
  tilt?: number;
};

const School: React.FC<SchoolProps> = ({
  rig,
  count,
  center,
  radius,
  height,
  scale,
  speed,
  phase,
  frame,
  yawOffset = 0,
  tilt = 0,
}) => {
  const copies = useMemo(
    () => (rig ? Array.from({ length: count }, () => rig.clone(true)) : []),
    [rig, count],
  );

  if (!rig) {
    return null;
  }

  const time = frame / 24;

  return (
    <group>
      {copies.map((copy, index) => {
        const offset = (index / count) * Math.PI * 2;
        const angle = time * speed + phase + offset;
        const r = radius + Math.sin(time * 0.7 + index) * 0.5;
        const x = center[0] + Math.cos(angle) * r;
        const z = center[2] + Math.sin(angle) * r;
        const y = center[1] + Math.sin(time * 1.1 + offset * 2) * 0.35 + Math.sin(offset * 3) * height;
        const heading = -angle + yawOffset;
        const wag = Math.sin(time * 7 + index * 1.7) * 0.08;
        return (
          <primitive
            key={index}
            object={copy}
            position={[x, y, z]}
            rotation={[tilt + Math.sin(time * 1.6 + index) * 0.06, heading, wag]}
            scale={scale}
          />
        );
      })}
    </group>
  );
};

/**
 * Penyu hijau dari `assets/env/sea_turtle.blend`.
 * Model menghadap +X; offset Y memusatkan badan di titik orbit.
 */
const Turtle: React.FC<{ ready: boolean; frame: number; center: [number, number, number] }> = ({
  ready,
  frame,
  center,
}) => {
  const turtle = useMemo(() => (ready ? cloneAsset("turtle") : null), [ready]);
  if (!turtle) {
    return null;
  }

  const time = frame / 24;
  const angle = time * 0.16 - 0.56;
  const radius = 1.6;
  const scale = 0.38;

  return (
    <primitive
      object={turtle}
      position={[
        center[0] + Math.cos(angle) * radius,
        center[1] - 0.85 * scale + Math.sin(time * 0.5) * 0.25,
        center[2] + Math.sin(angle) * radius,
      ]}
      rotation={[0.05, -angle - Math.PI / 2, Math.sin(time * 0.8) * 0.06]}
      scale={scale}
    />
  );
};

const SeaLife: React.FC<{ ready: boolean; frame: number }> = ({ ready, frame }) => {
  const rigs = useMemo(() => {
    if (!ready) {
      return null;
    }
    const source = getAsset("reef");
    if (!source) {
      return null;
    }
    source.updateMatrixWorld(true);
    return {
      cakalang: makeRig(source, "fish_cakalang"),
      hiu: makeRig(source, "fish_hiu"),
      goropa: makeRig(source, "fish_goropa-merah"),
      kakatua: makeRig(source, "fish_kakatua"),
      damselfish: makeRig(source, "fish_damselfish"),
      surgeon: makeRig(source, "fish_surgeon"),
    };
  }, [ready]);

  if (!rigs) {
    return null;
  }

  return (
    <group>
      <School
        rig={rigs.cakalang}
        count={12}
        center={[REEF[0] + 2, -3.3, REEF[2] + 1]}
        radius={6.5}
        height={0.7}
        scale={1.0}
        speed={0.22}
        phase={0.3}
        frame={frame}
      />
      <School
        rig={rigs.cakalang}
        count={18}
        center={[REEF[0] + 2, -2.6, REEF[2] + 7]}
        radius={5}
        height={1.1}
        scale={0.55}
        speed={0.19}
        phase={1.7}
        frame={frame}
      />
      <School
        rig={rigs.goropa}
        count={10}
        center={[REEF[0] - 1.5, -4.3, REEF[2] - 1]}
        radius={3.6}
        height={0.4}
        scale={0.75}
        speed={0.3}
        phase={2.1}
        frame={frame}
      />
      <School
        rig={rigs.kakatua}
        count={8}
        center={[REEF[0] + 3.5, -4.8, REEF[2] + 2.5]}
        radius={4.6}
        height={0.3}
        scale={0.7}
        speed={0.26}
        phase={4.2}
        frame={frame}
      />
      <School
        rig={rigs.damselfish}
        count={28}
        center={[REEF[0] - 2.5, -4.2, REEF[2] + 1.5]}
        radius={3.4}
        height={0.8}
        scale={0.5}
        speed={0.38}
        phase={3.0}
        frame={frame}
      />
      <School
        rig={rigs.surgeon}
        count={16}
        center={[REEF[0] + 5, -3.6, REEF[2] + 2]}
        radius={4.2}
        height={0.5}
        scale={0.8}
        speed={0.24}
        phase={5.1}
        frame={frame}
      />
      <School
        rig={rigs.hiu}
        count={1}
        center={[REEF[0] + 13, -2.0, REEF[2] - 18]}
        radius={10}
        height={0}
        scale={1.0}
        speed={0.14}
        phase={1.2}
        frame={frame}
      />
      <Turtle ready={ready} frame={frame} center={[REEF[0] + 0.5, -4.3, REEF[2] - 1]} />
    </group>
  );
};

/* ------------------------------------------------------------------ */
/* Perahu, karakter, dermaga                                           */
/* ------------------------------------------------------------------ */

const Boat: React.FC<{ ready: boolean; frame: number }> = ({ ready, frame }) => {
  const boat = useMemo(() => (ready ? cloneAsset("boat") : null), [ready]);
  const nara = useMemo(() => (ready ? cloneAsset("nara") : null), [ready]);
  if (!boat || !nara) {
    return null;
  }
  const time = frame / 24;
  return (
    <group position={BOAT_CENTER} rotation={[0, BOAT_YAW, 0]}>
      <group
        position={[0, Math.sin(time * 1.1) * 0.05, 0]}
        rotation={[Math.sin(time * 0.9) * 0.012, 0, Math.sin(time * 0.7 + 1) * 0.018]}
      >
        <primitive object={boat} />
        {/* Nara berdiri di buritan, baru naik dari air (tanpa rig; blockout). */}
        <primitive object={nara} position={[-2.0, 0.55, 0]} rotation={[0, -0.9, 0]} />
      </group>
    </group>
  );
};

type NaraProps = { ready: boolean; frame: number; dive: boolean };

/** Nara penyelam di depan terumbu — melayang, sedikit bergoyang. */
const NaraDiving: React.FC<NaraProps> = ({ ready, frame }) => {
  const nara = useMemo(() => (ready ? cloneAsset("nara") : null), [ready]);
  if (!nara) {
    return null;
  }
  const time = frame / 24;
  const yaw = Math.PI * 0.92;
  return (
    <primitive
      object={nara}
      position={[28.5 + Math.sin(time * 0.4) * 0.12, -4.5 + Math.sin(time * 0.8) * 0.07, 57.5]}
      rotation={[0.34, yaw + Math.sin(time * 0.5) * 0.04, Math.sin(time * 0.6) * 0.05]}
    />
  );
};

const Daniel: React.FC<{ ready: boolean }> = ({ ready }) => {
  const daniel = useMemo(() => (ready ? cloneAsset("daniel") : null), [ready]);
  if (!daniel) {
    return null;
  }
  return (
    <primitive object={daniel} position={[1.4, PIER_Y, 8]} rotation={[0.16, 0.5, 0]} />
  );
};

const NaraAtPier: React.FC<{ ready: boolean; frame: number }> = ({ ready, frame }) => {
  const nara = useMemo(() => (ready ? cloneAsset("nara") : null), [ready]);
  if (!nara) {
    return null;
  }
  const time = frame / 24;
  return (
    <primitive
      object={nara}
      position={[-0.4, PIER_Y, 100]}
      rotation={[0, Math.sin(time * 0.35) * 0.05, 0]}
    />
  );
};

/** Anak-anak: belum ada aset, sementara memakai Nara yang diperkecil. */
const Kids: React.FC<{ ready: boolean; frame: number }> = ({ ready, frame }) => {
  const nara = useMemo(() => (ready ? cloneAsset("nara") : null), [ready]);
  if (!nara) {
    return null;
  }
  const time = frame / 24;
  const kids = [
    { x: -1.2, z: 38, offset: 0, speed: 3.2 },
    { x: 0.6, z: 41, offset: 1.4, speed: 3.0 },
    { x: -0.2, z: 44, offset: 2.6, speed: 3.5 },
  ];
  return (
    <group>
      {kids.map((kid, index) => {
        const z = kid.z + ((time * kid.speed + kid.offset) % 7);
        return (
          <primitive
            key={index}
            object={index === 0 ? nara : nara.clone(true)}
            position={[kid.x, PIER_Y, z]}
            rotation={[0, 0, 0]}
            scale={0.62}
          />
        );
      })}
    </group>
  );
};

/* ------------------------------------------------------------------ */
/* Dunia                                                               */
/* ------------------------------------------------------------------ */

export const World: React.FC<{ ready: boolean; shot: Shot3D; frame: number }> = ({ ready, shot, frame }) => {
  const surface = useMemo(() => (ready ? cloneAsset("surface") : null), [ready]);
  const underwater = shot.underwater;

  if (!ready) {
    return null;
  }

  return (
    <group>
      <hemisphereLight
        args={[underwater ? "#63C4C0" : "#C9DEE6", underwater ? "#0E4A54" : "#C7B48D", underwater ? 1.25 : 1.15]}
      />
      <ambientLight intensity={underwater ? 0.5 : 0.22} color={underwater ? "#3FA9A5" : "#F2E9DC"} />
      <directionalLight
        position={underwater ? [-20, 40, -30] : [-120, 160, -90]}
        intensity={underwater ? 1.9 : 2.5}
        color={underwater ? "#D9F7EE" : "#FFE2B5"}
      />

      {/* Objek di atas air disembunyikan saat kamera bawah laut: dengan aset
          blockout, permukaan air belum menutupinya dengan benar. */}
      {!underwater && surface && <primitive object={surface} />}

      {/* dasar laut */}
      <mesh rotation-x={-Math.PI / 2} position={[REEF[0], SAND_Y, REEF[2]]}>
        <planeGeometry args={[260, 260, 1, 1]} />
        <meshStandardMaterial color="#C9B692" roughness={0.97} />
      </mesh>

      <Ocean frame={frame} underwater={underwater} />

      <ReefField ready={ready} />
      <ReefProps />
      <SeaLife ready={ready} frame={frame} />
      {underwater && <Plankton frame={frame} />}

      {!underwater && <Boat ready={ready} frame={frame} />}
      {(shot.id === "050" || shot.id === "060") && (
        <NaraDiving ready={ready} frame={frame} dive />
      )}
      {!underwater && <Daniel ready={ready} />}
      {!underwater && <NaraAtPier ready={ready} frame={frame} />}
      {!underwater && shot.id === "090" && <Kids ready={ready} frame={frame} />}
    </group>
  );
};
