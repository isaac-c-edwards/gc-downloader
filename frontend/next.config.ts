import path from "path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["lucide-react"],
  // Keep the build output in frontend/.next even when other lockfiles exist
  // in the monorepo (backend/package-lock.json triggers a wrong-root warning).
  turbopack: {
    root: path.join(__dirname),
  },
};

export default nextConfig;
