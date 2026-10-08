$ErrorActionPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Output "== 1. 停止 explorer 以释放图标缓存 =="
Stop-Process -Name explorer -Force
Start-Sleep -Seconds 3

Write-Output "== 2. 删除图标缓存数据库 =="
$cacheDir = Join-Path $env:LOCALAPPDATA 'Microsoft\Windows\Explorer'
$patterns = @('iconcache_*.db', 'thumbcache_*.db')
$n = 0
foreach ($p in $patterns) {
    Get-ChildItem -Path $cacheDir -Filter $p -Force -ErrorAction SilentlyContinue |
        ForEach-Object {
            Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue
            if (-not (Test-Path $_.FullName)) { $n++ }
        }
}
Write-Output ("  已删除 " + $n + " 个缓存文件")

Write-Output "== 3. 重启 explorer =="
Start-Process explorer.exe
Start-Sleep -Seconds 4

$explorer = Get-Process -Name explorer -ErrorAction SilentlyContinue
Write-Output ("  explorer 进程数 = " + (@($explorer).Count))
Write-Output "DONE"
