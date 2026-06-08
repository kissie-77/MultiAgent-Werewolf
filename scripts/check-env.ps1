<#
.SYNOPSIS
MultiAgent-Werewolf 本地开发环境自检工具 (Windows)

.DESCRIPTION
检查本机是否满足项目的完整开发环境要求，
并对缺失工具给出安装指引。

.PARAMETER SkipDocker
跳过 Docker 环境检查（仅本地开发时）

.PARAMETER SkipFrontend
跳过前端（Node.js / npm）检查（仅后端开发时）

.EXAMPLE
.\check-env.ps1                     # 检查全部
.\check-env.ps1 -SkipFrontend       # 仅后端
.\check-env.ps1 -SkipDocker         # 仅本地开发
#>
param(
    [switch]$SkipDocker,
    [switch]$SkipFrontend
)

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "  MultiAgent-Werewolf — 开发环境自检" -ForegroundColor Cyan
Write-Host "  ======================================" -ForegroundColor DarkCyan
Write-Host ""

$allOk = $true
$issues = @()

# ── 操作系统 ──────────────────────────────────────────────────────
$os = [System.Environment]::OSVersion
Write-Host "  操作系统  " -NoNewline -ForegroundColor Gray
Write-Host "$($os.Platform) / $($os.VersionString)" -ForegroundColor White

# ── Git ──────────────────────────────────────────────────────────
try {
    $ver = & git --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK]  Git    " -ForegroundColor Green -NoNewline
        Write-Host $ver
    } else {
        throw "not found"
    }
} catch {
    Write-Host "  [!!] Git    " -ForegroundColor Red -NoNewline
    Write-Host "未安装或不在 PATH 中" -ForegroundColor DarkYellow
    Write-Host "        安装: winget install --id Git.Git" -ForegroundColor DarkGray
    Write-Host "          或  https://git-scm.com/download/win" -ForegroundColor DarkGray
    $allOk = $false
    $issues += "Git 缺失"
}

# ── Python 3.10+ ─────────────────────────────────────────────────
try {
    $pyVer = & python --version 2>$null
    if ($LASTEXITCODE -eq 0 -and $pyVer -match "(\d+)\.(\d+)") {
        $major = [int]$Matches[1]
        $minor = [int]$Matches[2]
        if ($major -eq 3 -and $minor -ge 10) {
            Write-Host "  [OK]  Python " -ForegroundColor Green -NoNewline
            Write-Host $pyVer
        } else {
            Write-Host "  [!!] Python " -ForegroundColor Red -NoNewline
            Write-Host "$pyVer（需要 ≥ 3.10）" -ForegroundColor DarkYellow
            $allOk = $false
            $issues += "Python 版本过低"
        }
    } else {
        throw "not found"
    }
} catch {
    Write-Host "  [!!] Python " -ForegroundColor Red -NoNewline
    Write-Host "未安装或不在 PATH 中（需要 ≥ 3.10）" -ForegroundColor DarkYellow
    Write-Host "        安装: winget install Python.Python.3.12" -ForegroundColor DarkGray
    Write-Host "          或  https://python.org/downloads/" -ForegroundColor DarkGray
    $allOk = $false
    $issues += "Python 缺失"
}

# ── uv ───────────────────────────────────────────────────────────
try {
    $uvVer = & uv --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK]  uv     " -ForegroundColor Green -NoNewline
        Write-Host $uvVer
    } else {
        throw "not found"
    }
} catch {
    Write-Host "  [!!] uv     " -ForegroundColor Red -NoNewline
    Write-Host "未安装 — Python 依赖管理器" -ForegroundColor DarkYellow
    Write-Host "        安装: powershell -ExecutionPolicy ByPass -c `"irm https://astral.sh/uv/install.ps1 | iex`"" -ForegroundColor DarkGray
    Write-Host "        文档: https://docs.astral.sh/uv/" -ForegroundColor DarkGray
    $allOk = $false
    $issues += "uv 缺失"
}

# ── Node.js ──────────────────────────────────────────────────────
if (-not $SkipFrontend) {
    try {
        $nodeVer = & node --version 2>$null
        if ($LASTEXITCODE -eq 0 -and $nodeVer -match "^v(\d+)") {
            $nodeMajor = [int]$Matches[1]
            if ($nodeMajor -ge 18) {
                Write-Host "  [OK]  Node.js" -ForegroundColor Green -NoNewline
                Write-Host " $nodeVer"
            } else {
                Write-Host "  [!!] Node.js" -ForegroundColor Red -NoNewline
                Write-Host " $nodeVer（需要 ≥ 18）" -ForegroundColor DarkYellow
                $allOk = $false
                $issues += "Node.js 版本过低"
            }
        } else {
            throw "not found"
        }
    } catch {
        Write-Host "  [!!] Node.js" -ForegroundColor Red -NoNewline
        Write-Host " 未安装 — 前端开发依赖" -ForegroundColor DarkYellow
        Write-Host "        安装: winget install OpenJS.NodeJS.LTS" -ForegroundColor DarkGray
        Write-Host "          或  https://nodejs.org/en/download/" -ForegroundColor DarkGray
        $allOk = $false
        $issues += "Node.js 缺失"
    }

    # ── npm ──────────────────────────────────────────────────────────
    try {
        $npmVer = & npm --version 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [OK]  npm    " -ForegroundColor Green -NoNewline
            Write-Host " $npmVer"
        } else {
            throw "not found"
        }
    } catch {
        Write-Host "  [!!] npm    " -ForegroundColor Red -NoNewline
        Write-Host " 未安装 — 随 Node.js 自带，请检查安装" -ForegroundColor DarkYellow
        $allOk = $false
        $issues += "npm 缺失"
    }
}

# ── Docker (可选) ────────────────────────────────────────────────
if (-not $SkipDocker) {
    try {
        $dockerVer = & docker --version 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [OK]  Docker " -ForegroundColor Green -NoNewline
            Write-Host $dockerVer
            try {
                $composeVer = & docker compose version 2>$null
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "  [OK]  Compose" -ForegroundColor Green -NoNewline
                    Write-Host " 内置可用"
                } else {
                    Write-Host "  [--] Compose" -ForegroundColor Yellow -NoNewline
                    Write-Host " 未检测到，docker compose 命令可能不可用" -ForegroundColor DarkYellow
                }
            } catch {
                Write-Host "  [--] Compose" -ForegroundColor Yellow -NoNewline
                Write-Host " 未检测到" -ForegroundColor DarkYellow
            }
        } else {
            throw "not found"
        }
    } catch {
        Write-Host "  [--] Docker " -ForegroundColor Yellow -NoNewline
        Write-Host " 未安装（仅 Docker 部署时需要）" -ForegroundColor DarkYellow
        Write-Host "        安装: https://docs.docker.com/desktop/setup/install/windows-install/" -ForegroundColor DarkGray
    }
}

# ── 磁盘空间 ──────────────────────────────────────────────────────
Write-Host ""

# ── 汇总 ──────────────────────────────────────────────────────────
Write-Host "  --------------------------------------" -ForegroundColor DarkCyan
if ($allOk) {
    Write-Host ""
    Write-Host "  ✓  环境检查全部通过！" -ForegroundColor Green
    Write-Host ""
    Write-Host "  下一步：" -ForegroundColor White
    Write-Host "    make setup          # 一键初始化所有依赖（含前端 npm install）" -ForegroundColor Cyan
    Write-Host "    .\dev.ps1           # 启动全栈开发（API + Vite）" -ForegroundColor Cyan
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "  !  共发现 $($issues.Count) 个问题，请修复后重试。" -ForegroundColor Red
    foreach ($issue in $issues) {
        Write-Host "     - $issue" -ForegroundColor DarkYellow
    }
    Write-Host ""
    Write-Host "  修复后重新运行: .\scripts\check-env.ps1" -ForegroundColor DarkGray
    Write-Host ""
}

exit $(if ($allOk) { 0 } else { 1 })
