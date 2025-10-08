import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Music } from "lucide-react";

export function AudioPlayer({ urls }: { urls: string[] }) {
  const getTrackName = (url: string) => {
    const parts = url.split("?")[0].split("/");
    const fileName = parts[parts.length - 1];
    return fileName.replace(/_/g, " ").replace(".mp3", "");
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Separated Tracks</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {urls.map((url) => (
            <div key={url} className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <Music className="h-6 w-6 text-primary" />
                <p className="capitalize">{getTrackName(url)}</p>
              </div>
              <audio controls src={url} className="w-2/3" />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
