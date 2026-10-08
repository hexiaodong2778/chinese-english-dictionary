$WshShell = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath('Desktop')
$lnk = Join-Path $desktop '查单词.lnk'
if (Test-Path $lnk) { Remove-Item $lnk -Force }
$sc = $WshShell.CreateShortcut($lnk)
$sc.TargetPath = 'D:\Dictionary\查单词.exe'
$sc.WorkingDirectory = 'D:\Dictionary'
$sc.IconLocation = 'D:\Dictionary\查单词.exe,0'
$sc.Description = '查单词 - 多语言离线词典'
$sc.Save()
if (Test-Path $lnk) {
    Write-Output ("OK size=" + (Get-Item $lnk).Length)
} else {
    Write-Output 'FAILED'
}
