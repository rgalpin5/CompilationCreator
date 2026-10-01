import type { NextConfig } from "next";

const desktop = process.env.DESKTOP_EXPORT === "1";

const nextConfig: NextConfig = {
  ...(desktop
    ? {
        output: "export" as const,
        images: { unoptimized: true },
        // Write studio/index.html so the desktop server's static mount finds it.
        trailingSlash: true,
        env: { NEXT_PUBLIC_API_URL: "", NEXT_PUBLIC_EDITION: "desktop" },
      }
    : {}),
};

export default nextConfig;
