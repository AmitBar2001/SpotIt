import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  tasks: defineTable({
    request: v.object({
      songUrl: v.string(),
      start_time: v.optional(v.number()),
      duration: v.optional(v.number()),
    }),
    status: v.union(
      v.literal("pending"),
      v.literal("in_progress"),
      v.literal("completed"),
      v.literal("failed")
    ),
    message: v.string(),
    updatedAt: v.number(),
    songId: v.optional(v.id("songs")),
  }),
  songs: defineTable({
    originalUrl: v.string(),
    stemsUrls: v.object({
      drums: v.union(v.string(), v.null()),
      bass: v.union(v.string(), v.null()),
      guitar: v.union(v.string(), v.null()),
      other: v.union(v.string(), v.null()),
      original: v.string(),
    }),
    metadata: v.object({
      title: v.string(),
      artists: v.array(v.string()),
      album: v.optional(v.string()),
      duration: v.number(),
      youtube_views: v.number(),
      year: v.number(),
    }),
  }),
});
