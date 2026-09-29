import type { NextConfig } from "next";

// O navegador só fala com o Next; o Next repassa /api/* para a API Python.
// Assim não há CORS e a URL da API não vai para o cliente.
const API_URL = process.env.API_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_URL}/:path*` }];
  },
};

export default nextConfig;
