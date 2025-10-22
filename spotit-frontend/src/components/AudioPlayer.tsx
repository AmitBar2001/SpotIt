import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Music } from "lucide-react";
import React, { useEffect, useRef, useState } from "react";

export function AudioPlayer({ urls }: { urls: string[] }) {
  const getTrackName = (url: string) => {
    const parts = url.split("?")[0].split("/");
    const fileName = parts[parts.length - 1];
    return fileName.replace(/_/g, " ").replace(".mp3", "");
  };

  // Custom audio player with slider
  const AudioWithSlider = ({ url, initialVolume = 1 }: { url: string, initialVolume: number; }) => {
    const audioRef = useRef<HTMLAudioElement>(null);
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(0);

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = initialVolume;
    }
  }, [initialVolume]); // Re-run effect if initialVolume changes

    const handleTimeUpdate = () => {
      if (audioRef.current) {
        setCurrentTime(audioRef.current.currentTime);
      }
    };

    const handleLoadedMetadata = () => {
      if (audioRef.current) {
        setDuration(audioRef.current.duration);
      }
    };

    const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      const time = Number(e.target.value);
      setCurrentTime(time);
      if (audioRef.current) {
        audioRef.current.currentTime = time;
      }
    };

    return (
      <div className="w-full flex flex-col items-center">
        <audio
          ref={audioRef}
          controls={true}
          src={url}
          className="w-full h-12"
          onTimeUpdate={handleTimeUpdate}
          onLoadedMetadata={handleLoadedMetadata}
        />
        <input
          type="range"
          min={0}
          max={duration || 0}
          value={currentTime}
          onChange={handleSliderChange}
          className="w-full mt-2 accent-primary"
          step="0.01"
        />
        <div className="text-xs text-muted-foreground mt-1">
          {Math.floor(currentTime)}s / {Math.floor(duration)}s
        </div>
      </div>
    );
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Separated Tracks</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-8">
          {urls.map((url, index) => (
            <div key={url} className="flex flex-col items-start space-y-2">
              <div className="flex items-center space-x-4">
                <Music className="h-6 w-6 text-primary" />
                <p className="capitalize font-semibold">{getTrackName(url)}</p>
              </div>
              <AudioWithSlider url={url} initialVolume={index == urls.length - 1 ? 0.8: 1}/>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
