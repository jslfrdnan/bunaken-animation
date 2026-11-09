import { useEffect, useState } from "react";
import { staticFile, useDelayRender } from "remotion";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";

/**
 * Pemuatan aset GLB hasil ekspor `scenes/scene-1.blend`.
 *
 * Semua model sudah dalam koordinat dunia Blender yang dikonversi glTF
 * (Y-up): three `x = blender x`, `y = blender z`, `z = -blender y`.
 * Jadi model tidak perlu digeser lagi — cukup ditempatkan di titik yang sama
 * dengan yang dipakai di file Blender.
 */

export type AssetKey = "surface" | "reef" | "boat" | "nara" | "daniel" | "turtle";

export const ASSET_FILES: Record<AssetKey, string> = {
  surface: "models/env-surface.glb",
  reef: "models/env-reef.glb",
  boat: "models/boat.glb",
  nara: "models/char-nara.glb",
  daniel: "models/char-daniel.glb",
  turtle: "models/sea-turtle.glb",
};

const KEYS = Object.keys(ASSET_FILES) as AssetKey[];

const cache = new Map<AssetKey, THREE.Group>();
let pending: Promise<void> | null = null;

/**
 * Material Blender yang diekspor dengan mode alpha BLEND membuat objek
 * menembus air (perahu terlihat dari bawah laut). Karena semua aset masih
 * blockout, paksa jadi opaque supaya depth test bekerja normal.
 */
const normalizeMaterials = (root: THREE.Object3D) => {
  root.traverse((child) => {
    const mesh = child as THREE.Mesh;
    if (!mesh.isMesh) {
      return;
    }
    const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    for (const material of materials) {
      if (material.transparent || material.depthWrite === false) {
        material.transparent = false;
        material.opacity = 1;
        material.depthWrite = true;
        material.needsUpdate = true;
      }
    }
    mesh.castShadow = false;
    mesh.receiveShadow = false;
  });
};

const startLoading = (): Promise<void> => {
  if (pending) {
    return pending;
  }
  const loader = new GLTFLoader();
  pending = Promise.all(
    KEYS.map(
      (key) =>
        new Promise<void>((resolve, reject) => {
          loader.load(
            staticFile(ASSET_FILES[key]),
            (gltf) => {
              normalizeMaterials(gltf.scene);
              cache.set(key, gltf.scene);
              resolve();
            },
            undefined,
            reject,
          );
        }),
    ),
  ).then(() => undefined);
  return pending;
};

/**
 * Menahan render Remotion sampai keenam GLB siap, supaya tidak ada frame
 * kosong di awal render.
 */
export const useAssets = (): boolean => {
  const { delayRender, continueRender } = useDelayRender();
  const [handle] = useState(() => delayRender("Memuat aset 3D Scene 1"));
  const [ready, setReady] = useState(() => KEYS.every((k) => cache.has(k)));

  useEffect(() => {
    if (ready) {
      return;
    }
    let alive = true;
    startLoading().then(() => {
      if (alive) {
        setReady(true);
      }
    });
    return () => {
      alive = false;
    };
  }, [ready]);

  useEffect(() => {
    if (!ready) {
      return;
    }
    // Satu frame tambahan supaya three sempat menggambar scene sebelum
    // Remotion mengambil gambar.
    const id = requestAnimationFrame(() => continueRender(handle));
    return () => cancelAnimationFrame(id);
  }, [ready, handle, continueRender]);

  return ready;
};

/** Salinan model supaya satu GLB bisa dipakai berkali-kali (Nara, karang, dsb.). */
export const cloneAsset = (key: AssetKey): THREE.Group | null => {
  const source = cache.get(key);
  if (!source) {
    return null;
  }
  return source.clone(true);
};

export const getAsset = (key: AssetKey): THREE.Group | null => cache.get(key) ?? null;

/** Menggabungkan beberapa bagian (badan + sirip) jadi satu grup yang bisa digerakkan. */
export const makeRig = (source: THREE.Group, match: string): THREE.Group | null => {
  const parts = source.children.filter((child) => child.name.toLowerCase().includes(match));
  return groupParts(parts);
};

/** Versi yang mencocokkan nama objek persis (mis. `..._coral` vs `..._coral_b`). */
export const makeRigExact = (source: THREE.Group, names: string[]): THREE.Group | null => {
  const wanted = new Set(names.map((name) => name.toLowerCase()));
  const parts = source.children.filter((child) => wanted.has(child.name.toLowerCase()));
  return groupParts(parts);
};

const groupParts = (parts: THREE.Object3D[]): THREE.Group | null => {
  if (parts.length === 0) {
    return null;
  }
  const box = new THREE.Box3();
  for (const part of parts) {
    box.expandByObject(part);
  }
  const center = box.getCenter(new THREE.Vector3());
  const group = new THREE.Group();
  for (const part of parts) {
    const copy = part.clone(true);
    copy.position.sub(center);
    group.add(copy);
  }
  return group;
};
