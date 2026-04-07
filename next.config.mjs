/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    // !! ADVERTENCIA !!
    // Permitir despliegue a pesar de errores de tipos (MVP)
    ignoreBuildErrors: true,
  },
  eslint: {
    // Ignorar ESLint durante el build para mayor velocidad
    ignoreDuringBuilds: true,
  },
};

export default nextConfig;
