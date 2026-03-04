import { v } from "convex/values";
import { query } from "./_generated/server";

export const getSongs = query({
  args: { limit: v.optional(v.number()) },
  handler: async (ctx, args) => {
    return await ctx.db
      .query("songs")
      .order("desc")
      .take(args.limit || 50);
  },
});

export const getSong = query({
  args: { songId: v.id("songs") },
  handler: async (ctx, args) => {
    return await ctx.db.get(args.songId);
  },
});
