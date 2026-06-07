# MultiAgent-Werewolf — 开发快捷命令
# 前提：已安装 uv（https://docs.astral.sh/uv/getting-started/installation/）
# 使用：make <target>

.DEFAULT_GOAL := help
UV  := uv
RUN := $(UV) run
PYTHON := $(RUN) python

# ─── 颜色 ───────────────────────────────────────────────────────────────────
BOLD  := \033[1m
RESET := \033[0m
GREEN := \033[32m
CYAN  := \033[36m

# ─── 帮助 ───────────────────────────────────────────────────────────────────
.PHONY: help
help:
	@echo ""
	@echo "$(BOLD)MultiAgent-Werewolf 开发命令$(RESET)"
	@echo ""
	@echo "$(CYAN)环境$(RESET)"
	@echo "  $(BOLD)make setup$(RESET)          一键初始化：安装所有依赖 + 创建 .env + 配置 pre-commit"
	@echo "  $(BOLD)make install$(RESET)        仅安装运行时 + 开发 + 测试依赖（不含 docs）"
	@echo "  $(BOLD)make install-all$(RESET)    安装全部依赖组（含 docs）"
	@echo ""
	@echo "$(CYAN)测试$(RESET)"
	@echo "  $(BOLD)make test$(RESET)           运行所有测试（含覆盖率）"
	@echo "  $(BOLD)make test-fast$(RESET)      快速测试（无覆盖率，并行加速）"
	@echo "  $(BOLD)make test-file f=<path>$(RESET)  运行单个测试文件"
	@echo ""
	@echo "$(CYAN)代码质量$(RESET)"
	@echo "  $(BOLD)make lint$(RESET)           运行 ruff 检查"
	@echo "  $(BOLD)make fmt$(RESET)            运行 ruff 格式化"
	@echo "  $(BOLD)make check$(RESET)          lint + test（CI 入口）"
	@echo ""
	@echo "$(CYAN)运行游戏$(RESET)"
	@echo "  $(BOLD)make demo$(RESET)           Demo 模式（6 人，无需 API Key）"
	@echo "  $(BOLD)make demo9$(RESET)          Demo 模式（9 人，含警徽流）"
	@echo "  $(BOLD)make api$(RESET)            启动 FastAPI 服务（:8000）"
	@echo "  $(BOLD)make dev-web$(RESET)        启动前端 Vite 开发服（:5173，代理 /api → :8000）"
	@echo ""
	@echo "$(CYAN)Docker 部署$(RESET)"
	@echo "  $(BOLD)make docker-up$(RESET)      构建并启动所有容器（后台）"
	@echo "  $(BOLD)make docker-down$(RESET)    停止并移除容器"
	@echo "  $(BOLD)make docker-logs$(RESET)    跟踪所有容器日志"
	@echo "  $(BOLD)make docker-build$(RESET)   仅构建镜像"
	@echo ""

# ─── 环境 ───────────────────────────────────────────────────────────────────
.PHONY: setup
setup: _check-uv _reports-dir
	@echo "$(GREEN)▶ 安装依赖（dev + test 组）...$(RESET)"
	$(UV) sync --group dev --group test
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "$(GREEN)✔ 已创建 .env（请填入 API Key）$(RESET)"; \
	else \
		echo "  .env 已存在，跳过"; \
	fi
	@echo "$(GREEN)▶ 安装 pre-commit hooks...$(RESET)"
	$(RUN) pre-commit install --install-hooks 2>/dev/null || true
	@echo ""
	@echo "$(GREEN)✅ 环境初始化完成！$(RESET)"
	@echo "   下一步：编辑 .env 填入 API Key，然后运行 $(BOLD)make demo$(RESET) 测试。"

.PHONY: install
install: _check-uv _reports-dir
	$(UV) sync --group dev --group test

.PHONY: install-all
install-all: _check-uv _reports-dir
	$(UV) sync --all-groups

# ─── 测试 ───────────────────────────────────────────────────────────────────
.PHONY: test
test: _reports-dir
	$(RUN) pytest

.PHONY: test-fast
test-fast:
	$(RUN) pytest --override-ini="addopts=" --ignore=tests/scripts -q -n auto --tb=short

.PHONY: test-file
test-file:
	$(RUN) pytest $(f) --override-ini="addopts=" -v --tb=short

# ─── 代码质量 ─────────────────────────────────────────────────────────────
.PHONY: lint
lint:
	$(RUN) ruff check src/ tests/

.PHONY: fmt
fmt:
	$(RUN) ruff format src/ tests/
	$(RUN) ruff check --fix src/ tests/

.PHONY: check
check: lint test

# ─── 运行游戏（本地）────────────────────────────────────────────────────────
.PHONY: demo
demo:
	$(RUN) werewolf configs/demo-6.yaml

.PHONY: demo9
demo9:
	$(RUN) werewolf configs/demo-6.yaml --players 9 --badge_flow

.PHONY: api
api:
	$(RUN) werewolf-api

.PHONY: dev-web
dev-web:
	cd frontend && npm install && npm run dev

.PHONY: fleet
fleet:
	$(RUN) werewolf-fleet up --backends 2

# ─── Docker 部署 ──────────────────────────────────────────────────────────
.PHONY: docker-up
docker-up:
	docker compose up -d --build

.PHONY: docker-down
docker-down:
	docker compose down

.PHONY: docker-logs
docker-logs:
	docker compose logs -f

.PHONY: docker-build
docker-build:
	docker compose build

# ─── 内部辅助 ─────────────────────────────────────────────────────────────
.PHONY: _check-uv
_check-uv:
	@command -v uv >/dev/null 2>&1 || { \
		echo "❌ 未找到 uv，请先安装："; \
		echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"; \
		exit 1; \
	}

.PHONY: _reports-dir
_reports-dir:
	@mkdir -p .github/reports
