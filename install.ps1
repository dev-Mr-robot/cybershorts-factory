$ErrorActionPreference = 'Stop'
$app = $PSScriptRoot
$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
if (-not (($userPath -split ';') -contains $app)) {
    $newPath = if ($userPath) { "$userPath;$app" } else { $app }
    [Environment]::SetEnvironmentVariable('Path', $newPath, 'User')
}
& (Join-Path $app 'Cyber.cmd') --setup
Write-Output 'Open a new PowerShell window and run Cyber.'
