import {
  internalMutation,
  internalAction,
  internalQuery,
} from "./_generated/server";
import { v } from "convex/values";
import { internal } from "./_generated/api";

export const getSongsToMigrate = internalQuery({
  args: {},
  handler: async (ctx) => {
    const songs = await ctx.db.query("songs").collect();
    return songs.filter((song) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const metadata = song.metadata as any;
      return (
        typeof metadata.album === "string" ||
        metadata.album === undefined ||
        !metadata.album.images
      );
    });
  },
});

export const updateSongMetadata = internalMutation({
  args: {
    songId: v.id("songs"),
    metadata: v.any(),
  },
  handler: async (ctx, args) => {
    await ctx.db.patch(args.songId, {
      metadata: args.metadata,
    });
  },
});

export const enrichMetadataAction = internalAction({
  args: {},
  handler: async (ctx) => {
    const songs = await ctx.runQuery(internal.migrations.getSongsToMigrate);
    const backendUrl = "https://amitbar2001-spotit.hf.space";
    // const backendUrl = "http://localhost:8000"; // For local testing

    let count = 0;
    for (const song of songs) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const currentMetadata = song.metadata as any;
      const query = `${currentMetadata.title} ${currentMetadata.artists[0]}`;

      console.log(`Processing: ${query}`);

      try {
        const response = await fetch(
          `${backendUrl}/search-track/?query=${encodeURIComponent(query)}`,
          {
            headers: {
              "x-api-key": process.env.BACKEND_API_KEY || "",
            },
          },
        );

        if (response.ok) {
          const newMetadata = await response.json();
          // Preserve fields that might be more accurate from the original source if needed,
          // but the request was to use the endpoint.
          // However, youtube_views is 0 from spotify, so we should keep the old one if it exists.

          const mergedMetadata = {
            ...newMetadata,
            youtube_views:
              currentMetadata.youtube_views || newMetadata.youtube_views,
            // Keep original duration if it differs significantly?
            // Spotify duration is usually accurate.
          };

          await ctx.runMutation(internal.migrations.updateSongMetadata, {
            songId: song._id,
            metadata: mergedMetadata,
          });
          count++;
        } else {
          console.warn(`Failed to find track for ${query}: ${response.status}`);
          // Fallback: convert to new format without enrichment
          if (typeof currentMetadata.album === "string") {
            await ctx.runMutation(internal.migrations.updateSongMetadata, {
              songId: song._id,
              metadata: {
                ...currentMetadata,
                album: {
                  name: currentMetadata.album,
                  images: [],
                },
              },
            });
          }
        }
      } catch (e) {
        console.error(`Error processing ${query}:`, e);
      }
    }
    return `Enriched ${count} songs.`;
  },
});
