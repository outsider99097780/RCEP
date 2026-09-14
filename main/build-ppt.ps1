$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$marpCommand = Join-Path $projectRoot 'node_modules\.bin\marp.cmd'

if (-not (Test-Path -LiteralPath $marpCommand)) {
    throw 'Marp CLI was not found. Run npm install in the project root.'
}

$sourceCandidates = @(
    Get-ChildItem -LiteralPath $PSScriptRoot -Filter '*.md' -File |
        Where-Object {
            Select-String -LiteralPath $_.FullName -SimpleMatch 'marp: true' -Quiet
        }
)

if ($sourceCandidates.Count -ne 1) {
    throw "Expected exactly one Marp source in main, found $($sourceCandidates.Count)."
}

$sourceFile = $sourceCandidates[0].FullName
$outputFile = [System.IO.Path]::ChangeExtension($sourceFile, '.pptx')

$browserCandidates = @(
    'C:\Program Files\Google\Chrome\Application\chrome.exe',
    'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
    'C:\Program Files\Microsoft\Edge\Application\msedge.exe'
)
$browserPath = $browserCandidates |
    Where-Object { Test-Path -LiteralPath $_ } |
    Select-Object -First 1

if (-not $browserPath) {
    throw 'Chrome or Edge is required to export PPTX.'
}

$browserKind = if ($browserPath -match 'msedge\.exe$') { 'edge' } else { 'chrome' }

& $marpCommand `
    --allow-local-files `
    --browser $browserKind `
    --browser-path $browserPath `
    --browser-timeout 120 `
    --pptx `
    $sourceFile `
    -o $outputFile

if ($LASTEXITCODE -ne 0) {
    throw "Marp export failed with exit code $LASTEXITCODE."
}

Write-Host "PPTX generated: $outputFile"
