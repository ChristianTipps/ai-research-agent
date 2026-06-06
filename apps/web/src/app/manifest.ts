import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "AI Research Agent",
    short_name: "AI Research",
    description: "Learning-centered AI research workspace.",
    start_url: "/",
    display: "standalone",
    background_color: "#f4f7f2",
    theme_color: "#087f73",
    icons: [
      {
        src: "/icon.svg",
        sizes: "any",
        type: "image/svg+xml",
      },
    ],
  };
}
