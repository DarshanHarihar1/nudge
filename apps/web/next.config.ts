import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@nudge/db", "@nudge/ai", "@nudge/bot"],
};

export default nextConfig;
