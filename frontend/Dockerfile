# ─── 阶段 1：构建 React SPA ───────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# 只复制 package 文件，利用层缓存
COPY package.json package-lock.json* ./
RUN npm ci --prefer-offline

# 复制源码并构建
COPY . .
RUN npm run build

# ─── 阶段 2：nginx 静态服务 ───────────────────────────────────────────────
FROM nginx:1.27-alpine AS runtime

# 移除默认配置
RUN rm /etc/nginx/conf.d/default.conf

# 复制 nginx 站点配置（由 docker-compose 挂载或在这里 COPY）
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
