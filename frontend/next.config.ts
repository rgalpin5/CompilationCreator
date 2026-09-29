import type { NextConfig } from "next";

const desktop = process.env.DESKTOP_EXPORT === "1";

const nextConfig: NextConfig = {
  ...(desktop
    ? {
        output: "export" as const,
        images: { unoptimized: true },
        env: { NEXT_PUBLIC_API_URL: "" },
      }
    : {}),
};

export default nextConfig;
