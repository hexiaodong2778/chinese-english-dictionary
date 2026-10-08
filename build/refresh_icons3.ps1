$ErrorActionPreference = "SilentlyContinue"
Stop-Process -Name explorer -Force
Start-Sleep -Seconds 2
$dir = "$env:LOCALAPPDATA\Microsoft\Windows\Explorer"
$n = 0
Get-ChildItem $dir -Filter "iconcache_*.db" | ForEach-Object { Remove-Item $_.FullName -Force; $n++ }
Get-ChildItem $dir -Filter "thumbcache_*.db" | ForEach-Object { Remove-Item $_.FullName -Force; $n++ }
Start-Sleep -Seconds 1
Start-Process explorer.exe
Start-Sleep -Seconds 3
$ex = (Get-Process explorer | Measure-Object).Count
Write-Output "deleted=$n explorer=$ex"
