import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  /* config options here */
  
  // Set Turbopack root to monorepo root
  turbopack: {
    root: path.resolve(__dirname, "../.."),
  },
};

export default nextConfig;
