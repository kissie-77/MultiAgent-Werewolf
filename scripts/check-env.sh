#!/usr/bin/env bash
# MultiAgent-Werewolf — 本地开发环境自检工具 (macOS / Linux)
#
# Usage:
#   bash scripts/check-env.sh              # 检查全部
#   bash scripts/check-env.sh --skip-frontend  # 仅后端
#   bash scripts/check-env.sh --skip-docker    # 仅本地开发

set -euo pipefail

SKIP_FRONTEND=false
SKIP_DOCKER=false
for arg in "$@"; do
  case "$arg" in
    --skip-frontend) SKIP_FRONTEND=true ;;
    --skip-docker)   SKIP_DOCKER=true ;;
  esac
done

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
WHITE='\033[0;37m'
BOLD='\033[1m'
RESET='\033[0m'

all_ok=true
issues=()

echo ""
echo -e "${CYAN}  MultiAgent-Werewolf — 开发环境自检${RESET}"
echo -e "${CYAN}  ======================================${RESET}"
echo ""

# ── 操作系统 ──────────────────────────────────────────────────────
os_name="$(uname -s)"
os_ver="$(uname -r)"
echo -e "  ${GRAY}操作系统  ${os_name} / ${os_ver}${RESET}"

# ── Git ──────────────────────────────────────────────────────────
if command -v git &>/dev/null; then
  ver=$(git --version 2>/dev/null || true)
  echo -e "  ${GREEN}[OK]${RESET}  Git    ${ver}"
else
  echo -e "  ${RED}[!!]${RESET}  Git    ${YELLOW}未安装或不在 PATH 中${RESET}"
  echo -e "        ${GRAY}安装: brew install git (macOS) / apt install git (Ubuntu)${RESET}"
  all_ok=false
  issues+=("Git 缺失")
fi

# ── Python 3.10+ ─────────────────────────────────────────────────
if command -v python3 &>/dev/null; then
  py=$(python3 --version 2>/dev/null || true)
  if [[ "$py" =~ ([0-9]+)\.([0-9]+) ]]; then
    major=${BASH_REMATCH[1]}
    minor=${BASH_REMATCH[2]}
    if [[ $major -eq 3 && $minor -ge 10 ]]; then
      echo -e "  ${GREEN}[OK]${RESET}  Python ${py}"
    else
      echo -e "  ${RED}[!!]${RESET}  Python ${YELLOW}${py}（需要 ≥ 3.10）${RESET}"
      all_ok=false
      issues+=("Python 版本过低")
    fi
  fi
else
  echo -e "  ${RED}[!!]${RESET}  Python ${YELLOW}未安装（需要 ≥ 3.10）${RESET}"
  echo -e "        ${GRAY}安装: brew install python@3.12 (macOS) / apt install python3 (Ubuntu)${RESET}"
  echo -e "        ${GRAY}  或  https://python.org/downloads/${RESET}"
  all_ok=false
  issues+=("Python 缺失")
fi

# ── uv ───────────────────────────────────────────────────────────
if command -v uv &>/dev/null; then
  ver=$(uv --version 2>/dev/null || true)
  echo -e "  ${GREEN}[OK]${RESET}  uv     ${ver}"
else
  echo -e "  ${RED}[!!]${RESET}  uv     ${YELLOW}未安装 — Python 依赖管理器${RESET}"
  echo -e "        ${GRAY}安装: curl -LsSf https://astral.sh/uv/install.sh | sh${RESET}"
  echo -e "        ${GRAY}文档: https://docs.astral.sh/uv/${RESET}"
  all_ok=false
  issues+=("uv 缺失")
fi

# ── Node.js ──────────────────────────────────────────────────────
if [[ "$SKIP_FRONTEND" != true ]]; then
  if command -v node &>/dev/null; then
    node_ver=$(node --version 2>/dev/null || true)
    if [[ "$node_ver" =~ ^v([0-9]+) ]]; then
      node_major=${BASH_REMATCH[1]}
      if [[ $node_major -ge 18 ]]; then
        echo -e "  ${GREEN}[OK]${RESET}  Node.js ${node_ver}"
      else
        echo -e "  ${RED}[!!]${RESET}  Node.js ${YELLOW}${node_ver}（需要 ≥ 18）${RESET}"
        all_ok=false
        issues+=("Node.js 版本过低")
      fi
    fi
  else
    echo -e "  ${RED}[!!]${RESET}  Node.js ${YELLOW}未安装 — 前端开发依赖${RESET}"
    echo -e "        ${GRAY}安装: brew install node (macOS) / apt install nodejs (Ubuntu)${RESET}"
    echo -e "        ${GRAY}  或  https://nodejs.org/en/download/${RESET}"
    all_ok=false
    issues+=("Node.js 缺失")
  fi

  # ── npm ──────────────────────────────────────────────────────────
  if command -v npm &>/dev/null; then
    ver=$(npm --version 2>/dev/null || true)
    echo -e "  ${GREEN}[OK]${RESET}  npm     ${ver}"
  else
    echo -e "  ${RED}[!!]${RESET}  npm     ${YELLOW}未安装 — 随 Node.js 自带${RESET}"
    all_ok=false
    issues+=("npm 缺失")
  fi
fi

# ── Docker (可选) ────────────────────────────────────────────────
if [[ "$SKIP_DOCKER" != true ]]; then
  if command -v docker &>/dev/null; then
    ver=$(docker --version 2>/dev/null || true)
    echo -e "  ${GREEN}[OK]${RESET}  Docker  ${ver}"
    if docker compose version &>/dev/null; then
      echo -e "  ${GREEN}[OK]${RESET}  Compose 内置可用"
    else
      echo -e "  ${YELLOW}[--]${RESET} Compose ${YELLOW}未检测到${RESET}"
    fi
  else
    echo -e "  ${YELLOW}[--]${RESET} Docker  ${YELLOW}未安装（仅 Docker 部署时需要）${RESET}"
    echo -e "        ${GRAY}安装: https://docs.docker.com/desktop/${RESET}"
  fi
fi

# ── 汇总 ──────────────────────────────────────────────────────────
echo ""
echo -e "  ${CYAN}--------------------------------------${RESET}"
if [[ "$all_ok" == true ]]; then
  echo ""
  echo -e "  ${GREEN}✓  环境检查全部通过！${RESET}"
  echo ""
  echo -e "  ${WHITE}下一步：${RESET}"
  echo -e "    ${CYAN}make setup          ${RESET}# 一键初始化所有依赖（含前端 npm install）"
  echo -e "    ${CYAN}./dev.sh            ${RESET}# 启动全栈开发（API + Vite）"
  echo ""
else
  echo ""
  echo -e "  ${RED}!  共发现 ${#issues[@]} 个问题，请修复后重试。${RESET}"
  for issue in "${issues[@]}"; do
    echo -e "     ${YELLOW}- $issue${RESET}"
  done
  echo ""
  echo -e "  ${GRAY}修复后重新运行: bash scripts/check-env.sh${RESET}"
  echo ""
fi

if [[ "$all_ok" == true ]]; then exit 0; else exit 1; fi
