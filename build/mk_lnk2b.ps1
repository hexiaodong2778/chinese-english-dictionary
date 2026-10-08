chcp 65001 > $null
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 桌面路径用 API 取，避免中文字面量编码问题
$desktop = [Environment]::GetFolderPath('Desktop')
# 文件名用 Unicode 码点构造，彻底避开脚本编码问题
$name = [string]::Join('', @(
    [char]0x67E5, [char]0x5355, [char]0x8BCD, '.lnk'
))
$lnkPath = Join-Path $desktop $name
Write-Output ("desktop = " + $desktop)
Write-Output ("lnkPath = " + $lnkPath)

# 目标 exe 路径也用码点构造
$exeName = [string]::Join('', @([char]0x67E5, [char]0x5355, [char]0x8BCD, '.exe'))
$target = 'D:\Dictionary\' + $exeName
Write-Output ("target  = " + $target)
Write-Output ("exists  = " + (Test-Path $target))

if (Test-Path $lnkPath) { Remove-Item $lnkPath -Force }

$WshShell = New-Object -ComObject WScript.Shell
$sc = $WshShell.CreateShortcut($lnkPath)
$sc.TargetPath = $target
$sc.WorkingDirectory = 'D:\Dictionary'
$sc.IconLocation = $target + ',0'
$sc.Description = 'ChaDanCi - offline multilingual dictionary'
$sc.Save()

if (Test-Path $lnkPath) {
    Write-Output ("OK size=" + (Get-Item $lnkPath).Length)
} else {
    Write-Output 'FAILED'
}
