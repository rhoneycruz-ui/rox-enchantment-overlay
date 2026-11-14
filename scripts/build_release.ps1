param(
    # Python used to run PyInstaller. Defaults to the project's .venv.
    [string]$Python = ""
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not $Python) {
    $Python = Join-Path $projectRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $Python)) {
        throw "Python da .venv não encontrado em $Python. Crie a .venv e rode: pip install -e "".[dev]"""
    }
}
$spec = Join-Path $projectRoot "packaging\rox-overlay.spec"
$distRoot = Join-Path $projectRoot "dist"
$distribution = Join-Path $distRoot "ROX Enchantment Overlay"
$zip = Join-Path $distRoot "ROX-Enchantment-Overlay-portable.zip"

& $Python -m PyInstaller --clean --noconfirm --distpath $distRoot $spec
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Copy-Item -LiteralPath (Join-Path $projectRoot "README.md") -Destination $distribution -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "LICENSE") -Destination $distribution -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "THIRD_PARTY_NOTICES.md") -Destination $distribution -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "third_party") -Destination $distribution -Recurse -Force

if (Test-Path -LiteralPath $zip) { Remove-Item -LiteralPath $zip -Force }
Compress-Archive -Path $distribution -DestinationPath $zip
$hash = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content -LiteralPath "$zip.sha256" -Value "$hash  ROX-Enchantment-Overlay-portable.zip" -Encoding ascii

Write-Host "Distribuição pronta em: $distribution"
Write-Host "ZIP: $zip"
Write-Host "SHA-256: $hash"
