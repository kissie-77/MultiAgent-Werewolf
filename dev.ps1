# Start local full-stack dev: FastAPI (:8010) + Vite frontend.

# Usage (repo root):

#   .\dev.ps1

#   .\dev.ps1 -ApiPort 8010 -OpenBrowser

#   .\dev.ps1 -BackendOnly



param(

    [int]$ApiPort = 8010,

    [switch]$BackendOnly,

    [switch]$FrontendOnly,

    [switch]$OpenBrowser

)



$ErrorActionPreference = "Stop"

$RepoRoot = $PSScriptRoot

Set-Location $RepoRoot



$env:OBS_READY_REQUIRE_LLM = "0"

$env:PYTHONPATH = Join-Path $RepoRoot "src"



function Test-ApiHealth {

    param([int]$Port)

    try {

        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/health" -UseBasicParsing -TimeoutSec 2

        return $resp.StatusCode -eq 200

    } catch {

        return $false

    }

}



function Wait-ApiHealth {

    param([int]$Port, [int]$Seconds = 90)

    for ($i = 0; $i -lt $Seconds; $i++) {

        if (Test-ApiHealth -Port $Port) { return $true }

        Start-Sleep -Seconds 1

    }

    return $false

}



if (-not $FrontendOnly) {

    if (-not (Test-ApiHealth -Port $ApiPort)) {

        Write-Host "Starting backend on http://127.0.0.1:$ApiPort ..."

        $backendCmd = @(

            "-NoExit",

            "-Command",

            "Set-Location '$RepoRoot'; `$env:OBS_READY_REQUIRE_LLM='0'; `$env:PYTHONPATH='$($env:PYTHONPATH)'; uv run werewolf-api --port $ApiPort"

        )

        Start-Process -FilePath "powershell" -ArgumentList $backendCmd -PassThru -WindowStyle Normal | Out-Null

        if (-not (Wait-ApiHealth -Port $ApiPort)) {

            throw "Backend did not become healthy on port $ApiPort within 90s."

        }

        Write-Host "Backend ready: http://127.0.0.1:$ApiPort/health"

    } else {

        Write-Host "Backend already listening on port $ApiPort — reusing."

    }

}



if ($BackendOnly) {

    Write-Host "Backend-only mode. Close the API window to stop."

    return

}



Set-Location (Join-Path $RepoRoot "frontend")

if (-not (Test-Path "node_modules")) {

    Write-Host "Installing frontend dependencies..."

    npm install

}



Write-Host "Starting Vite (proxy -> http://127.0.0.1:$ApiPort via frontend/.env.development)..."

if ($OpenBrowser) {

    Start-Process "http://localhost:5173"

}



npm run dev

