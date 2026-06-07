# ─── 阶段 1：构建前端静态资源 ─────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# 依赖安装（利用 Docker 缓存层）
COPY package.json package-lock.json* ./
RUN npm ci

# 复制源码并构建
COPY . .
RUN npm run build

# ─── 阶段 2：Nginx 生产服务 ──────────────────────────────────────────────
FROM nginx:alpine AS runtime

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 Nginx 配置（反代 /api 到后端）
# 注意：此文件需与 Dockerfile 放在同一构建上下文中
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
