$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  throw "Docker Desktop is required."
}
docker compose version | Out-Null

if (-not (Test-Path ".env")) {
  Copy-Item ".env.docker.example" ".env"
  Write-Host "Created .env from the safe Docker template."
}

$withAI = $args -contains "--with-ai"
$withGPU = $args -contains "--with-ai-gpu"
if ($withGPU) { $withAI = $true }
$composeFiles = @()
if ($withGPU) { $composeFiles = @("-f", "docker-compose.yml", "-f", "docker-compose.gpu.yml") }
if ($withAI) {
  $env:OSIEL_OLLAMA_ENABLED = "true"
  $env:OSIEL_OLLAMA_DOCKER_BASE_URL = "http://ollama:11434"
  docker compose @composeFiles up --build -d --wait api web
  docker compose @composeFiles --profile ai up -d --wait ollama
  docker compose @composeFiles --profile ai run --rm ollama-models
  docker compose @composeFiles restart api | Out-Null
  docker compose @composeFiles up -d --wait api web
} else {
  docker compose up --build -d --wait api web
}

Write-Host "OSIEL application: http://localhost:3000"
Write-Host "Python API docs:  http://localhost:8000/v1/docs"
