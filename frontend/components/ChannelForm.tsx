"use client";

import { useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type Props = {
  loading: boolean;
  error: string | null;
  onSubmit: (url: string) => void;
};

export default function ChannelForm({ loading, error, onSubmit }: Props) {
  const [url, setUrl] = useState("");

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = url.trim();
    if (trimmed) onSubmit(trimmed);
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col gap-2 rounded-xl bg-card p-3 shadow-sm ring-1 ring-foreground/10"
    >
      <div className="flex gap-2">
        <Input
          type="url"
          placeholder="https://www.youtube.com/@channel"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          aria-label="YouTube channel URL"
          disabled={loading}
        />
        <Button type="submit" disabled={loading || !url.trim()}>
          {loading ? "Loading…" : "Load videos"}
        </Button>
      </div>
      {loading && (
        <p className="text-sm text-muted-foreground">Fetching videos…</p>
      )}
      {error && <p className="text-sm text-destructive">{error}</p>}
    </form>
  );
}
