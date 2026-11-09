import { Composition } from "remotion";
import { Scene1Animatic } from "./Scene1Animatic";
import { Scene1ThreeD } from "./Scene1ThreeD";
import { FPS, TOTAL_FRAMES } from "./shots";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="Scene1ThreeD"
        component={Scene1ThreeD}
        durationInFrames={TOTAL_FRAMES}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{ slate: true }}
      />
      <Composition
        id="Scene1Animatic"
        component={Scene1Animatic}
        durationInFrames={TOTAL_FRAMES}
        fps={FPS}
        width={1920}
        height={1080}
        defaultProps={{ slate: true }}
      />
    </>
  );
};
