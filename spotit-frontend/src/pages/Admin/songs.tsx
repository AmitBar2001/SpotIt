import { useQuery } from "convex/react";
import { api } from "../../../convex/_generated/api";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardTitle,
  CardHeader,
  CardDescription,
} from "@/components/ui/card";
import { Loader2, Music, Play, Disc, Calendar, Eye } from "lucide-react";
import { Link } from "react-router-dom";

export default function SongsDashboard() {
  const songs = useQuery(api.songs.getSongs, { limit: 100 });

  if (songs === undefined) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Processed Songs</h2>
        <p className="text-sm text-muted-foreground">
          {songs.length} songs in database
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3 sm:gap-4">
        {songs.map((song) => (
          <Card
            key={song._id}
            className="overflow-hidden flex flex-col h-full group py-0 gap-0"
          >
            <div className="relative aspect-square sm:h-40 overflow-hidden shrink-0">
              {song.metadata.album.images?.[0] ? (
                <img
                  src={song.metadata.album.images[0]}
                  alt={song.metadata.title}
                  className="object-cover w-full h-full transition-transform duration-500 group-hover:scale-110"
                />
              ) : (
                <div className="flex items-center justify-center h-full bg-muted">
                  <Music className="h-10 w-10 text-muted-foreground/20" />
                </div>
              )}

              {/* Overlay with title and artist using CardHeader components */}
              <CardHeader className="absolute inset-0 bg-linear-to-t from-black/90 via-black/40 to-transparent flex flex-col justify-end p-2.5 pb-3 space-y-0 gap-0.5 z-10">
                <CardTitle className="text-xs sm:text-sm font-bold text-white line-clamp-1">
                  {song.metadata.title}
                </CardTitle>
                <CardDescription className="text-[10px] sm:text-[11px] text-gray-300 line-clamp-1">
                  {song.metadata.artists.join(", ")}
                </CardDescription>
              </CardHeader>

              <div className="absolute top-2 left-2 sm:top-3 sm:left-3 bg-black/60 text-white text-[10px] sm:text-[10px] px-1.5 py-0.5 rounded backdrop-blur-sm font-medium z-20">
                {Math.floor(song.metadata.duration / 60)}:
                {String(Math.floor(song.metadata.duration % 60)).padStart(
                  2,
                  "0",
                )}
              </div>

              {/* Floating Play Button */}
              <Button
                size="icon"
                className="absolute bottom-2 right-2 sm:bottom-3 sm:right-3 h-8 w-8 sm:h-10 sm:w-10 rounded-full shadow-lg bg-primary hover:bg-primary/90 hover:scale-110 transition-all z-20"
                asChild
              >
                <Link to={`/?sid=${song._id}`} title="Play Song">
                  <Play className="h-4 w-4 sm:h-5 sm:w-5 fill-current" />
                </Link>
              </Button>
            </div>

            <CardContent className="p-2.5 pb-1 flex-1 flex flex-col justify-center gap-1">
              <div className="flex items-center gap-3 text-[10px] sm:text-[10px] text-muted-foreground">
                <div className="flex items-center gap-1 shrink-0">
                  <Calendar className="h-2.5 w-2.5 sm:h-3 shrink-0" />
                  <span className="font-medium text-foreground/80">
                    {song.metadata.year}
                  </span>
                </div>

                <div className="flex items-center gap-1 shrink-0">
                  <Eye className="h-2.5 w-2.5 sm:h-3 shrink-0" />
                  <span className="font-medium text-foreground/80">
                    {song.metadata.youtube_views.toLocaleString()}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-1 text-[10px] sm:text-[10px] text-muted-foreground overflow-hidden">
                <Disc className="h-2.5 w-2.5 sm:h-3 shrink-0" />
                <span className="truncate font-medium text-foreground/80">
                  {song.metadata.album.name}
                </span>
              </div>
            </CardContent>

            <CardFooter className="p-2.5 pt-0 flex justify-end">
              <span className="text-[9px] sm:text-[10px] text-muted-foreground font-medium uppercase tracking-wider">
                {new Date(song._creationTime).toLocaleDateString()}
              </span>
            </CardFooter>
          </Card>
        ))}
        {songs.length === 0 && (
          <div className="text-center py-20 border-2 border-dashed rounded-lg col-span-full">
            <p className="text-muted-foreground italic">
              No songs found in the database.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
