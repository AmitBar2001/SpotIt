import { NuqsAdapter } from "nuqs/adapters/react-router/v6";
import { BrowserRouter } from "react-router-dom";
import { URLInputForm } from "@/components/URLInputForm";
import { AudioPlayer } from "@/components/AudioPlayer";
import {
  ConvexProvider,
  ConvexReactClient,
  useMutation,
  useQuery,
} from "convex/react";
import * as z from "zod";
import { useEffect } from "react";
import { api } from "../convex/_generated/api";
import type { Id } from "../convex/_generated/dataModel.d.ts";
import { triggerColdBoot } from "@/api";
import { useQueryState } from "nuqs";

const convex = new ConvexReactClient(import.meta.env.VITE_CONVEX_URL as string);

// eslint-disable-next-line @typescript-eslint/no-unused-vars
const FormSchema = z.object({
  url: z.string().url(),
});

function App() {
  useEffect(() => {
    triggerColdBoot();
  }, []);
  const [taskId, setTaskId] = useQueryState("tid");

  const createTask = useMutation(api.tasks.createTask);
  const task = useQuery(
    api.tasks.getTask,
    taskId ? { taskId: taskId as Id<"tasks"> } : "skip"
  );

  const onSubmit = async (data: z.infer<typeof FormSchema>) => {
    try {
      const newTaskId = await createTask({ songUrl: data.url });
      setTaskId(newTaskId);
    } catch (e) {
      console.error("Failed to create task", e);
    }
  };

  const isLoading =
    taskId !== null &&
    (task === undefined ||
      task?.status === "pending" ||
      task?.status === "in_progress");
  const error = task?.status === "failed" ? task.message : null;

  let urls: string[] = [];
  if (task?.song?.stemsUrls) {
    const s = task.song.stemsUrls;
    urls = [s.drums, s.bass, s.guitar, s.other, s.original];
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-secondary font-sans antialiased">
      <div className="container relative flex min-h-screen flex-col items-center justify-center">
        <div className="flex w-full max-w-md flex-col items-center space-y-8 rounded-lg bg-card p-8 shadow-lg">
          <h1 className="text-5xl font-bold tracking-tighter text-primary">
            SpotIt
          </h1>
          <p className="text-muted-foreground">
            Separate audio tracks from your favorite songs.
          </p>
          <URLInputForm onSubmit={onSubmit} isLoading={isLoading} />
          {isLoading && <p>Processing... {task?.message || ""}</p>}
          {error && <p className="text-red-500">Error: {error}</p>}
          {urls.length > 0 && <AudioPlayer urls={urls} />}
        </div>
      </div>
    </div>
  );
}

export default function WrappedApp() {
  return (
    <NuqsAdapter>
      <BrowserRouter>
        <ConvexProvider client={convex}>
          <App />
        </ConvexProvider>
      </BrowserRouter>
    </NuqsAdapter>
  );
}
