param([string]$Map, [int]$Seconds = 90, [string]$Shot = "")
# Launch WC3 1.27b with -loadfile and watch for a crash (BlizzardError) or early exit.
if ($env:WC3_DIR) { $wc3 = $env:WC3_DIR } else { $wc3 = "C:\Program Files (x86)\Warcraft III" }
$errDir = Join-Path $env:TEMP "BlizzardError"
Get-Process BlizzardError, war3 -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep 1
$before = @(Get-ChildItem $errDir -Recurse -Filter Crash.txt -ErrorAction SilentlyContinue | ForEach-Object FullName)
$p = Start-Process -FilePath "$wc3\war3.exe" -ArgumentList @("-window", "-loadfile", "`"$Map`"") -WorkingDirectory $wc3 -PassThru
$t0 = Get-Date
$status = "running"
while (((Get-Date) - $t0).TotalSeconds -lt $Seconds) {
    Start-Sleep 2
    if (Get-Process BlizzardError -ErrorAction SilentlyContinue) { $status = "CRASH (BlizzardError)"; break }
    if ($p.HasExited) { $status = "EXITED code $($p.ExitCode)"; break }
}
$el = [int]((Get-Date) - $t0).TotalSeconds
if ($Shot -and -not $p.HasExited) {
    Add-Type -AssemblyName System.Windows.Forms, System.Drawing
    $b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    $bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size)
    $bmp.Save($Shot, [System.Drawing.Imaging.ImageFormat]::Png)
    $g.Dispose(); $bmp.Dispose()
}
"status=$status after ${el}s; ws=$([int]($p.WorkingSet64/1MB))MB"
$new = @(Get-ChildItem $errDir -Recurse -Filter Crash.txt -ErrorAction SilentlyContinue | Where-Object { $before -notcontains $_.FullName })
foreach ($c in $new) { "--- $($c.FullName)"; Get-Content $c.FullName -TotalCount 40 }
