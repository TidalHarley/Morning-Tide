import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const repo = process.env.GITHUB_REPOSITORY?.split("/")[1];
  const base =
    process.env.VITE_BASE || (mode === "production" && repo ? `/${repo}/` : "/");

  return {
    base,
  server: {
    host: "0.0.0.0", // 允许所有网络接口访问
    port: 8080,
    strictPort: false, // 如果端口被占用，自动尝试下一个端口
    open: true, // 自动打开浏览器
    hmr: {
      overlay: false,
    },
  },
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  };
});
