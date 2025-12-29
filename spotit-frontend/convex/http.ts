import { httpRouter } from "convex/server";
import { httpAction } from "./_generated/server";
import { internal } from "./_generated/api";
import { Id } from "./_generated/dataModel";

const http = httpRouter();

http.route({
  path: "/update-task",
  method: "POST",
  handler: httpAction(async (ctx, req) => {
    const url = new URL(req.url);
    const taskIdString = url.searchParams.get("taskId");

    if (!taskIdString) {
      return new Response("Missing taskId", { status: 400 });
    }

    const taskId = taskIdString as Id<"tasks">;
    const body = await req.json();

    try {
      await ctx.runMutation(internal.tasks.handleTaskUpdate, {
        taskId,
        payload: body,
      });
    } catch (e: unknown) {
      console.error("Error updating task", e);
      return new Response(
        `Error: ${e instanceof Error ? e.message : "Unknown error"}`,
        { status: 500 }
      );
    }

    return new Response("OK", { status: 200 });
  }),
});

export default http;
