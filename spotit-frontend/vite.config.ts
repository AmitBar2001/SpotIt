import path from "path";
import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import dotenv from "dotenv";

dotenv.config();

// https://vite.dev/config/
export default defineConfig({
  base: "/SpotIt",
  plugins: [
    react({
      babel: {
        plugins: [["babel-plugin-react-compiler"]],
      },
    }),
    tailwindcss(),
    process.env.VITE_MOCK_API === "true" && mockApiPlugin(),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});

function mockApiPlugin(): Plugin {
  return {
    name: "mock-api",
    configureServer(server) {
      server.middlewares.use("/api", (req, res, next) => {
        if (req.method === "POST") {
          setTimeout(() => {
            const presignedUrls = [
              "https://storage.googleapis.com/audio-outputs/drums.mp3",
              "https://storage.googleapis.com/audio-outputs/drums_bass.mp3",
              "https://storage.googleapis.com/audio-outputs/drums_bass_guitar.mp3",
              "https://storage.googleapis.com/audio-outputs/drums_bass_guitar_other_piano.mp3",
              "https://storage.googleapis.com/audio-outputs/original_trimmed.mp3",
            ];
            res.setHeader("Content-Type", "application/json");
            res.end(JSON.stringify(presignedUrls));
          }, 3000);
        } else {
          next();
        }
      });
    },
  };
}
