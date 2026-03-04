import { Music, ClipboardList } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import SongsDashboard from "./songs";
import TasksDashboard from "./tasks";

export default function Admin() {
  return (
    <div className="container mx-auto py-6 px-4">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Admin Dashboard</h1>
        <p className="text-muted-foreground mt-1">
          Manage background tasks and view processed songs.
        </p>
      </div>

      <Tabs defaultValue="tasks" className="w-full">
        <TabsList className="mb-4">
          <TabsTrigger value="tasks" className="flex items-center gap-2">
            <ClipboardList className="h-4 w-4" />
            Tasks
          </TabsTrigger>
          <TabsTrigger value="songs" className="flex items-center gap-2">
            <Music className="h-4 w-4" />
            Songs
          </TabsTrigger>
        </TabsList>

        <TabsContent value="tasks" className="mt-0">
          <TasksDashboard />
        </TabsContent>

        <TabsContent value="songs" className="mt-0">
          <SongsDashboard />
        </TabsContent>
      </Tabs>
    </div>
  );
}
