import { v } from "convex/values";
import {
  mutation,
  internalMutation,
  internalAction,
  query,
} from "./_generated/server";
import { internal } from "./_generated/api";

const TaskStatusUpdateValidator = v.object({
  status: v.union(
    v.literal("pending"),
    v.literal("in_progress"),
    v.literal("completed"),
    v.literal("failed")
  ),
  message: v.union(v.string(), v.null()),
});

const SongMetadataValidator = v.object({
  title: v.string(),
  artists: v.array(v.string()),
  album: v.string(),
  duration: v.number(),
  youtube_views: v.number(),
  year: v.number(),
});

const UpdateTaskBodyValidator = v.object({
  task_status: TaskStatusUpdateValidator,
  song_metadata: SongMetadataValidator,
  file_keys: v.object({
    drums: v.string(),
    bass: v.string(),
    guitar: v.string(),
    other: v.string(),
    original: v.string(),
  }),
});

export const handleTaskUpdate = internalMutation({
  args: {
    taskId: v.id("tasks"),
    payload: v.union(TaskStatusUpdateValidator, UpdateTaskBodyValidator),
  },
  handler: async (ctx, args) => {
    const payload = args.payload;

    if ("song_metadata" in payload) {
      // UpdateTaskBody
      const stems = payload.file_keys;
      const metadata = payload.song_metadata;

      // Create song
      const songId = await ctx.db.insert("songs", {
        originalUrl: stems.original,
        stemsUrls: {
          drums: stems.drums,
          bass: stems.bass,
          guitar: stems.guitar,
          other: stems.other,
          original: stems.original,
        },
        metadata: {
          title: metadata.title,
          artists: metadata.artists,
          album: metadata.album,
          duration: metadata.duration,
          youtube_views: metadata.youtube_views,
          year: metadata.year,
        },
      });

      // Update task
      await ctx.db.patch(args.taskId, {
        status: "completed",
        message: "Process complete",
        updatedAt: Date.now(),
        songId: songId,
      });
    } else {
      // TaskStatusUpdate
      await ctx.db.patch(args.taskId, {
        status: payload.status,
        message: payload.message || "",
        updatedAt: Date.now(),
      });
    }
  },
});

export const createTask = mutation({
  args: {
    songUrl: v.string(),
    start_time: v.optional(v.number()),
    duration: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    const taskId = await ctx.db.insert("tasks", {
      request: {
        songUrl: args.songUrl,
        start_time: args.start_time,
        duration: args.duration,
      },
      status: "pending",
      message: "Task created",
      updatedAt: Date.now(),
    });

    await ctx.scheduler.runAfter(0, internal.tasks.performSeparation, {
      taskId,
      songUrl: args.songUrl,
      start_time: args.start_time,
      duration: args.duration,
    });

    return taskId;
  },
});

export const getTask = query({
  args: { taskId: v.id("tasks") },
  handler: async (ctx, args) => {
    const task = await ctx.db.get(args.taskId);
    if (!task) return null;

    let song = null;
    if (task.songId) {
      song = await ctx.db.get(task.songId);
    }

    return {
      ...task,
      song,
    };
  },
});

export const performSeparation = internalAction({
  args: {
    taskId: v.id("tasks"),
    songUrl: v.string(),
    start_time: v.optional(v.number()),
    duration: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    const siteUrl = process.env.CONVEX_SITE_URL;
    if (!siteUrl) {
      throw new Error("CONVEX_SITE_URL is not defined");
    }

    const callback_url = `${siteUrl}/update-task?taskId=${args.taskId}`;
    const backendUrl = "https://amitbar2001-spotit.hf.space";
    const apiKey = process.env.BACKEND_API_KEY;

    if (!apiKey) {
      throw new Error("BACKEND_API_KEY is not defined");
    }

    const payload = {
      url: args.songUrl,
      start_time: args.start_time,
      duration: args.duration,
      callback_url: callback_url,
    };

    try {
      const response = await fetch(`${backendUrl}/separate-from-link/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-api-key": apiKey,
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`Backend request failed: ${response.statusText}`);
      }
    } catch (error: unknown) {
      // We manually construct the failure payload here to reuse the mutation logic
      const failurePayload = {
        status: "failed" as const,
        message: error instanceof Error ? error.message : "Unknown error",
      };

      await ctx.runMutation(internal.tasks.handleTaskUpdate, {
        taskId: args.taskId,
        payload: failurePayload,
      });
    }
  },
});
