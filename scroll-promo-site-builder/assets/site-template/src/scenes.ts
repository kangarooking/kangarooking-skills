export type Scene = {
  id: string;
  number: string;
  nav: string;
  eyebrow: string;
  title: string;
  body: string;
  tags: string[];
  still: string;
  start: number;
  accent: string;
};

// Replace these values from the approved storyboard and reviewed video timeline.
export const VIDEO_DURATION = 50;

export const scenes: Scene[] = [
  { id: "start", number: "01", nav: "起点", eyebrow: "__SCENE_01_EYEBROW__", title: "__SCENE_01_TITLE__", body: "__SCENE_01_BODY__", tags: ["__TAG__"], still: "/stills/scene-01.jpg", start: 0, accent: "#ff9b42" },
  { id: "understand", number: "02", nav: "理解", eyebrow: "__SCENE_02_EYEBROW__", title: "__SCENE_02_TITLE__", body: "__SCENE_02_BODY__", tags: ["__TAG__"], still: "/stills/scene-02.jpg", start: 10, accent: "#63b7f3" },
  { id: "validate", number: "03", nav: "验证", eyebrow: "__SCENE_03_EYEBROW__", title: "__SCENE_03_TITLE__", body: "__SCENE_03_BODY__", tags: ["__TAG__"], still: "/stills/scene-03.jpg", start: 20, accent: "#5ccb8a" },
  { id: "build", number: "04", nav: "构造", eyebrow: "__SCENE_04_EYEBROW__", title: "__SCENE_04_TITLE__", body: "__SCENE_04_BODY__", tags: ["__TAG__"], still: "/stills/scene-04.jpg", start: 30, accent: "#7f75e8" },
  { id: "deliver", number: "05", nav: "交付", eyebrow: "__SCENE_05_EYEBROW__", title: "__SCENE_05_TITLE__", body: "__SCENE_05_BODY__", tags: ["__TAG__"], still: "/stills/scene-05.jpg", start: 40, accent: "#ff6b61" },
];
