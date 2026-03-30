import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  poweredByHeader: false,
  transpilePackages: ["@tradenoc/config", "@tradenoc/types", "@tradenoc/ui"],
};

export default nextConfig;
