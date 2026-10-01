"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { YouTubeSession } from "./useYouTubePlayer";

type Props = {
  videoId: string;
  title: string;
  start: string;
  end: string;
  durationSeconds: number | null;
  disabled?: boolean;
  onChange: (patch: { start?: string; end?: string }) => void;
};

/** The clip card: title, player, and the trim controls under it. */
export default function ClipPlayer({
  videoId,
  title,
  start,
  end,
  durationSeconds,
  disabled,
  onChange,
}: Props) {
  return (
    <Card id="clip-player" className="scroll-mt-4 shadow-sm">
      <CardHeader className="border-b">
        <CardTitle className="line-clamp-2">{title}</CardTitle>
        <CardDescription>
          Play until the intro ends, then cut it. Jump to the ending and cut the outro the same way.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <YouTubeSession
          videoId={videoId}
          title={title}
          start={start}
          end={end}
          durationSeconds={durationSeconds}
          disabled={disabled}
          onChange={onChange}
        />
      </CardContent>
    </Card>
  );
}
