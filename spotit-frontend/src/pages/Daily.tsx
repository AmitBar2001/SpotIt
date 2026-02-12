import { AudioPlayer } from "@/components/AudioPlayer";
import { useQuery } from "convex/react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { api } from "../../convex/_generated/api";

// TODO: fix can't refresh.

export default function Daily() {
  const [showDetails, setShowDetails] = useState(false);
  const task = useQuery(api.tasks.getLatestDailyTask);

  const isLoading = task === undefined;

  return (
    <div className="container relative flex flex-1 flex-col items-center justify-center py-12">
      <div className="flex w-full max-w-md flex-col items-center space-y-8 rounded-lg bg-card p-8 shadow-lg">
        <h1 className="text-4xl font-bold tracking-tighter text-primary">
          Daily
        </h1>
        <p className="text-muted-foreground text-center">
          A random song selected from my liked songs in Spotify.
        </p>
        {isLoading && <p className="text-muted-foreground">Loading...</p>}

        {!isLoading && !task && (
          <p className="text-muted-foreground text-center">
            No daily song found yet.
          </p>
        )}

        {task?.song?.stemsUrls && (
          <div className="w-full flex flex-col items-center">
            <div className="flex justify-center items-center space-x-4 text-sm text-muted-foreground mb-4">
              <div className="flex items-center gap-1">
                <span className="font-medium">
                  {task.song.metadata.youtube_views.toLocaleString()}
                </span>
                <span>views</span>
              </div>
              <span>•</span>
              <span>{task.song.metadata.year}</span>
            </div>

            <AudioPlayer stems={task.song.stemsUrls} />

            <div className="mt-6 text-center w-full">
              <Button
                variant="secondary"
                onClick={() => setShowDetails(!showDetails)}
                className="w-full"
              >
                {showDetails ? "Hide Details" : "Show Details"}
              </Button>

              {showDetails && (
                <div className="mt-4 p-4 rounded-lg bg-secondary/50 text-left space-y-4 duration-3000 animate-in fade-in slide-in-from-top-8">
                  <div className="flex items-start gap-4">
                    {task.song.metadata.album.images[0] && (
                      <img
                        src={task.song.metadata.album.images[0]}
                        alt={task.song.metadata.album.name}
                        className="w-20 h-20 rounded-md object-cover shadow-sm"
                      />
                    )}
                    <div className="flex-1 min-w-0">
                      <h3
                        className="font-bold text-lg leading-tight truncate"
                        title={task.song.metadata.title}
                      >
                        {task.song.metadata.title}
                      </h3>
                      <p
                        className="text-muted-foreground truncate"
                        title={task.song.metadata.artists.join(", ")}
                      >
                        {task.song.metadata.artists.join(", ")}
                      </p>
                      <p
                        className="text-xs text-muted-foreground mt-1 truncate"
                        title={task.song.metadata.album.name}
                      >
                        {task.song.metadata.album.name}
                      </p>
                    </div>
                  </div>

                  <div className="flex justify-between items-center text-xs text-muted-foreground border-t pt-3">
                    <span>Duration</span>
                    <span className="font-mono">
                      {Math.floor(task.song.metadata.duration / 60)}:
                      {String(task.song.metadata.duration % 60).padStart(
                        2,
                        "0",
                      )}
                    </span>
                  </div>
                </div>
              )}
            </div>

            <span className="text-sm text-muted-foreground mt-4">
              {new Date(task._creationTime).toLocaleDateString()}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
