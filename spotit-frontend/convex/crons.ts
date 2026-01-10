import { cronJobs } from "convex/server";
import { api } from "./_generated/api";

const crons = cronJobs();

crons.daily(
  "trigger daily song",
  { hourUTC: 0, minuteUTC: 0 },
  api.daily_songs.triggerDailySong
);

export default crons;
