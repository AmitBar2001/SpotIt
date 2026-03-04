import { useMutation, useQuery } from "convex/react";
import { useState } from "react";
import { api } from "../../../convex/_generated/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardTitle } from "@/components/ui/card";
import { Loader2, RefreshCw, ExternalLink } from "lucide-react";
import type { Id } from "../../../convex/_generated/dataModel";

export default function TasksDashboard() {
  const tasks = useQuery(api.tasks.getTasks, { limit: 100 });
  const retryTask = useMutation(api.tasks.retryTask);
  const [expandedTasks, setExpandedTasks] = useState<Record<string, boolean>>(
    {},
  );

  const toggleExpand = (taskId: string) => {
    setExpandedTasks((prev) => ({
      ...prev,
      [taskId]: !prev[taskId],
    }));
  };

  const handleRetry = async (taskId: Id<"tasks">) => {
    try {
      await retryTask({ taskId });
    } catch (error) {
      console.error("Failed to retry task:", error);
    }
  };

  if (tasks === undefined) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Background Tasks</h2>
        <p className="text-sm text-muted-foreground">
          {tasks.length} tasks retrieved
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {tasks.map((task) => (
          <Card
            key={task._id}
            className="overflow-hidden border-l-4 h-full flex flex-col"
            style={{
              borderLeftColor:
                task.status === "completed"
                  ? "#22c55e"
                  : task.status === "failed"
                    ? "#ef4444"
                    : task.status === "in_progress"
                      ? "#3b82f6"
                      : "#94a3b8",
            }}
          >
            <div className="flex flex-row items-start justify-between space-y-0 pb-2 bg-muted/30 pt-3 px-4">
              <div className="flex flex-col min-w-0 pr-2">
                <CardTitle className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                  {task.type || "standard"} Task
                </CardTitle>
                <span className="text-[10px] font-mono text-muted-foreground mt-0.5 truncate">
                  ID: {task._id}
                </span>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <span
                  className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium shadow-sm ${
                    task.status === "completed"
                      ? "bg-green-100 text-green-800"
                      : task.status === "failed"
                        ? "bg-red-100 text-red-800"
                        : task.status === "in_progress"
                          ? "bg-blue-100 text-blue-800"
                          : "bg-gray-100 text-gray-800"
                  }`}
                >
                  {task.status}
                </span>
                {(task.status === "failed" || task.status === "pending") && (
                  <Button
                    size="icon"
                    variant="outline"
                    onClick={() => handleRetry(task._id)}
                    className="h-9 w-9 sm:h-8 sm:w-8"
                    title="Retry Task"
                  >
                    <RefreshCw className="h-4 w-4 sm:h-3.5 sm:w-3.5" />
                  </Button>
                )}
              </div>
            </div>
            <CardContent className="pt-3 pb-3 flex-1 flex flex-col">
              <div className="space-y-3 flex-1">
                <div>
                  <p className="text-[10px] font-semibold text-muted-foreground uppercase mb-1">
                    Source URL
                  </p>
                  <a
                    href={task.request.songUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="group inline-flex items-center gap-1 text-primary hover:text-primary/80 font-medium break-all underline decoration-primary/30 underline-offset-2 text-xs"
                  >
                    <span className="truncate max-w-[200px] sm:max-w-none inline-block">
                      {task.request.songUrl}
                    </span>
                    <ExternalLink className="h-3 w-3 shrink-0 opacity-50 group-hover:opacity-100 transition-opacity" />
                  </a>
                </div>

                <div className="flex gap-4">
                  {task.request.start_time !== undefined && (
                    <div>
                      <p className="text-[10px] font-semibold text-muted-foreground uppercase mb-0.5">
                        Start
                      </p>
                      <p className="font-mono text-xs">
                        {task.request.start_time}s
                      </p>
                    </div>
                  )}
                  {task.request.duration !== undefined && (
                    <div>
                      <p className="text-[10px] font-semibold text-muted-foreground uppercase mb-0.5">
                        Duration
                      </p>
                      <p className="font-mono text-xs">
                        {task.request.duration}s
                      </p>
                    </div>
                  )}
                </div>

                <div
                  className="cursor-pointer group/msg"
                  onClick={() => toggleExpand(task._id)}
                >
                  <p className="text-[10px] font-semibold text-muted-foreground uppercase mb-1 flex justify-between items-center">
                    Status Message
                    <span className="text-[9px] font-normal lowercase opacity-0 group-hover/msg:opacity-100 transition-opacity hidden sm:inline">
                      (click to toggle)
                    </span>
                  </p>
                  <p
                    className={`text-xs bg-muted/40 p-1.5 rounded border leading-snug transition-all ${
                      expandedTasks[task._id] ? "" : "line-clamp-2"
                    }`}
                  >
                    {task.message || "No status message reported."}
                  </p>
                </div>
              </div>

              <div className="mt-3 pt-2 border-t flex flex-col gap-1 text-[10px] text-muted-foreground">
                <div className="flex justify-between">
                  <span>CREATED</span>
                  <span className="font-medium text-foreground">
                    {new Date(task._creationTime).toLocaleString()}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>UPDATED</span>
                  <span className="font-medium text-foreground">
                    {new Date(task.updatedAt).toLocaleString()}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
        {tasks.length === 0 && (
          <div className="text-center py-20 border-2 border-dashed rounded-lg col-span-full">
            <p className="text-muted-foreground italic">
              No tasks found in the database.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
