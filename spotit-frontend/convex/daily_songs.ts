import { query, action } from "./_generated/server";
import { api } from "./_generated/api";

export const getToday = query({
  args: {},
  handler: async (ctx) => {
    const today = new Date().toISOString().split("T")[0];
    const daily = await ctx.db
      .query("daily_songs")
      .withIndex("by_date", (q) => q.eq("date", today))
      .first();
    
    if (!daily) return null;
    return await ctx.db.get(daily.songId);
  },
});

export const triggerDailySong = action({
  args: {},
  handler: async (ctx) => {
    const playlistUrl = process.env.LIKED_SONGS_PLAYLIST_URL;
    if (!playlistUrl) {
      throw new Error("LIKED_SONGS_PLAYLIST_URL is not defined");
    }

    await ctx.runMutation(api.tasks.createTask, {
      songUrl: playlistUrl,
      type: "daily",
    });
  },
});
