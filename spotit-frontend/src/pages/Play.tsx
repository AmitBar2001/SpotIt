import { URLInputForm } from "@/components/URLInputForm";
import { AudioPlayer } from "@/components/AudioPlayer";
import { useMutation, useQuery } from "convex/react";
import * as z from "zod";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { api } from "../../convex/_generated/api";
import type { Id } from "../../convex/_generated/dataModel.d.ts";
import { triggerColdBoot } from "@/api";
import { useQueryState } from "nuqs";

// eslint-disable-next-line @typescript-eslint/no-unused-vars
const FormSchema = z.object({
  url: z.string().url(),
});

export default function Play() {
  const [showDetails, setShowDetails] = useState(false);
  useEffect(() => {
    triggerColdBoot();
  }, []);
  const [taskId, setTaskId] = useQueryState("tid");
  const [songId, setSongId] = useQueryState("sid");

  const createTask = useMutation(api.tasks.createTask);
  const task = useQuery(
    api.tasks.getTask,
    taskId ? { taskId: taskId as Id<"tasks"> } : "skip",
  );

  const directSong = useQuery(
    api.songs.getSong,
    songId ? { songId: songId as Id<"songs"> } : "skip",
  );

  const displaySong = task?.song || directSong;

  const onSubmit = async (data: z.infer<typeof FormSchema>) => {
    try {
      setShowDetails(false);
      // Clear sid when starting a new task
      setSongId(null);
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

  return (
    <div className="container relative flex flex-1 flex-col items-center justify-center py-12">
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
        {displaySong?.stemsUrls && (
          <div className="w-full flex flex-col items-center">
            <div className="flex justify-center items-center space-x-4 text-sm text-muted-foreground mb-4">
              <div className="flex items-center gap-1">
                <span className="font-medium">
                  {displaySong.metadata.youtube_views.toLocaleString()}
                </span>
                <span>views</span>
              </div>
              <span>•</span>
              <span>{displaySong.metadata.year}</span>
            </div>

            <AudioPlayer stems={displaySong.stemsUrls} />

            <div className="mt-6 text-center w-full">
              <Button
                variant="secondary"
                onClick={() => setShowDetails(!showDetails)}
                className="w-full"
              >
                {showDetails ? "Hide Details" : "Show Details"}
              </Button>

              {showDetails && (
                <div className="mt-4 p-4 rounded-lg bg-secondary/50 text-left space-y-4 animate-in fade-in slide-in-from-top-2">
                  <div className="flex items-start gap-4">
                    {displaySong.metadata.album.images[0] && (
                      <img
                        src={displaySong.metadata.album.images[0]}
                        alt={displaySong.metadata.album.name}
                        className="w-20 h-20 rounded-md object-cover shadow-sm"
                      />
                    )}
                    <div className="flex-1 min-w-0">
                      <h3
                        className="font-bold text-lg leading-tight truncate"
                        title={displaySong.metadata.title}
                      >
                        {displaySong.metadata.title}
                      </h3>
                      <p
                        className="text-muted-foreground truncate"
                        title={displaySong.metadata.artists.join(", ")}
                      >
                        {displaySong.metadata.artists.join(", ")}
                      </p>
                      <p
                        className="text-xs text-muted-foreground mt-1 truncate"
                        title={displaySong.metadata.album.name}
                      >
                        {displaySong.metadata.album.name}
                      </p>
                    </div>
                  </div>

                  <div className="flex justify-between items-center text-xs text-muted-foreground border-t pt-3">
                    <span>Duration</span>
                    <span className="font-mono">
                      {Math.floor(displaySong.metadata.duration / 60)}:
                      {String(displaySong.metadata.duration % 60).padStart(
                        2,
                        "0",
                      )}
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
