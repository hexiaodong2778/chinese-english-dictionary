$ErrorActionPreference = 'SilentlyContinue'

Write-Output "== 1. Stop explorer to release icon cache =="
Stop-Process -Name explorer -Force
Start-Sleep -Seconds 3

Write-Output "== 2. Delete icon cache databases =="
$cacheDir = Join-Path $env:LOCALAPPDATA 'Microsoft\Windows\Explorer'
$n = 0
Get-ChildItem -Path $cacheDir -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like 'iconcache_*.db' -or $_.Name -like 'thumbcache_*.db' } |
    ForEach-Object {
        $p = $_.FullName
        Remove-Item $p -Force -ErrorAction SilentlyContinue
        if (-not (Test-Path $p)) { $n++ }
    }
Write-Output ("  deleted " + $n + " cache files")

Write-Output "== 3. Restart explorer =="
Start-Process explorer.exe
Start-Sleep -Seconds 5

$explorer = @(Get-Process -Name explorer -ErrorAction SilentlyContinue)
Write-Output ("  explorer processes = " + $explorer.Count)
Write-Output "DONE"
