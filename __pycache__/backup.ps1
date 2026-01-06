Set-Location "C:\dev\_new-project"

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$name = "pinpoint_backup_$ts.zip"

$paths = @(
  "app.py",
  "templates",
  "static",
  "instance",
  "Procfile",
  "README.md",
  "requirements.txt"
)

Compress-Archive -Path $paths -DestinationPath $name -Force

Write-Output "✅ Backup created: $name"
