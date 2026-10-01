"use client";

import { useEffect, useRef, useState } from "react";

/** A thumbnail that waits to load until it is near the viewport. */
export default function LazyThumbnail({ src }: { src: string | null }) {
  const ref = useRef<HTMLImageElement>(null);
  const [shown, setShown] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node || shown || !src) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setShown(true);
          observer.disconnect();
        }
      },
      { rootMargin: "200px" },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [shown, src]);

  if (!src) return null;

  return (
    // The source is attached only once the card is near the viewport.
    // eslint-disable-next-line @next/next/no-img-element
    <img
      ref={ref}
      src={shown ? src : undefined}
      alt=""
      className="h-full w-full object-cover"
      decoding="async"
    />
  );
}
