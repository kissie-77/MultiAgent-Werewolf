# ──────────────────────────────────────────────────────────────────────────
# 前端多阶段构建 Dockerfile
#
# Stage 1: Node.js 构建生产产物
# Stage 2: Nginx 提供静态文件服务
# ──────────────────────────────────────────────────────────────────────────

# ── Stage 1: 构建 ──────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# 复制依赖清单（利用 Docker 缓存层）
COPY package.json package-lock.json ./

# 安装依赖（仅生产依赖 + 构建依赖）
RUN npm ci --ignore-scripts && \
    npm cache clean --force

# 复制源代码
COPY . .

# 生产构建
ARG VITE_API_PROXY
ENV VITE_API_PROXY=${VITE_API_PROXY:-http://api:8000}

RUN npm run build

# ── Stage 2: 运行 ──────────────────────────────────────────────────────────
FROM nginx:1.27-alpine AS runner

# 安装基础安全工具
RUN apk add --no-cache curl

# 复制 Nginx 配置
COPY deploy/nginx-frontend.conf /etc/nginx/conf.d/default.conf

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 创建非 root 用户
RUN addgroup -g 1001 -S nginx-group && \
    adduser -S -D -H -u 1001 -s /sbin/nologin -G nginx-group -h /usr/share/nginx/html nginx-user && \
    chown -R nginx-user:nginx-group /usr/share/nginx/html && \
    chown -R nginx-user:nginx-group /var/cache/nginx && \
    chown -R nginx-user:nginx-group /var/log/nginx && \
    chown -R nginx-user:nginx-group /etc/nginx/conf.d && \
    touch /var/run/nginx.pid && \
    chown -R nginx-user:nginx-group /var/run/nginx.pid

USER nginx-user

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:80/ || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
