$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$pyinstaller = Join-Path $projectRoot ".venv\Scripts\pyinstaller.exe"
$spec = Join-Path $projectRoot "packaging\rox-overlay.spec"
$distribution = Join-Path $projectRoot "dist\ROX Enchantment Overlay"

if (-not (Test-Path -LiteralPath $pyinstaller)) {
    throw "PyInstaller não encontrado em $pyinstaller. Crie a .venv e instale as dependências de desenvolvimento primeiro."
}

& $pyinstaller --clean --noconfirm $spec
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Copy-Item -LiteralPath (Join-Path $projectRoot "README.md") -Destination $distribution -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "LICENSE") -Destination $distribution -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "THIRD_PARTY_NOTICES.md") -Destination $distribution -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "third_party") -Destination $distribution -Recurse -Force

Write-Host "Distribuição pronta em: $distribution"
