param(
    [Parameter(Mandatory=$true)][string]$InputPath,
    [Parameter(Mandatory=$true)][string]$OutputDirectory
)
$ErrorActionPreference = 'Stop'

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$inputResolved = (Resolve-Path -LiteralPath $InputPath).Path
$outputResolved = [System.IO.Path]::GetFullPath($OutputDirectory)
if (-not $outputResolved.StartsWith($projectRoot + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'Render output must stay inside theme2.'
}
New-Item -ItemType Directory -Force -Path $outputResolved | Out-Null
$powerpoint = $null
$presentation = $null
try {
    $powerpoint = New-Object -ComObject PowerPoint.Application
    if ($null -eq $powerpoint) { throw 'PowerPoint COM automation is unavailable in this session.' }
    $presentation = $powerpoint.Presentations.Open($inputResolved, $true, $false, $false)
    $presentation.Export($outputResolved, 'PNG', 1600, 900)
    Write-Output "Rendered $($presentation.Slides.Count) slides to $outputResolved"
}
finally {
    if ($presentation -ne $null) { $presentation.Close() }
    if ($powerpoint -ne $null) { $powerpoint.Quit() }
}
