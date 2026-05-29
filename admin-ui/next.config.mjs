/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // standalone output → Dockerfile.prod ใช้ build ขนาดเล็กลง 80%
  output: "standalone",
  // proxy /api → backend ตอน dev (เลี่ยง CORS)
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"}/:path*`,
      },
    ];
  },
};

export default nextConfig;
