param([string]$Cmd, [string]$A = "", [string]$B = "", [string]$C = "")
# Tiny UI driver for the WC3 window. Clicks/keys are only sent when war3 is the foreground window.
# shot <png> | click <x> <y> | rclick <x> <y> | key <vk> | text <string> | launch | front | move <x> <w> <h>
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
if (-not ([System.Management.Automation.PSTypeName]'PZUi4').Type) {
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class PZUi4 {
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint dx, uint dy, uint d, IntPtr e);
  [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte scan, uint f, IntPtr e);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
  [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr h);
  [DllImport("user32.dll")] public static extern bool MoveWindow(IntPtr h, int x, int y, int w, int hh, bool r);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, IntPtr pid);
  [DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
  [DllImport("user32.dll")] public static extern bool AttachThreadInput(uint a, uint b, bool f);
  public static void Force(IntPtr h) { IntPtr fg = GetForegroundWindow(); uint t1 = GetWindowThreadProcessId(fg, IntPtr.Zero); uint t2 = GetCurrentThreadId(); AttachThreadInput(t2, t1, true); ShowWindow(h, 9); BringWindowToTop(h); SetForegroundWindow(h); AttachThreadInput(t2, t1, false); }
}
"@
}
function W3 { Get-Process war3 -ErrorAction SilentlyContinue | Select-Object -First 1 }
function Front {
  $p = W3
  if (-not $p) { throw "war3 not running" }
  $h = $p.MainWindowHandle
  for ($i = 0; $i -lt 5; $i++) {
    if ([PZUi4]::GetForegroundWindow() -eq $h) { return }
    [PZUi4]::keybd_event(0x12,0,0,[IntPtr]::Zero); [PZUi4]::keybd_event(0x12,0,2,[IntPtr]::Zero)
    [PZUi4]::Force($h)
    Start-Sleep -Milliseconds 400
  }
  if ([PZUi4]::GetForegroundWindow() -ne $h) { throw "could not bring war3 to the foreground; not sending input" }
}
switch ($Cmd) {
  'launch' { Start-Process -FilePath (Join-Path $env:WC3_DIR "war3.exe") -ArgumentList "-window" -WorkingDirectory $env:WC3_DIR | Out-Null }
  'front' { Front; "foreground ok" }
  'move' { $p = W3; [PZUi4]::MoveWindow($p.MainWindowHandle, [int]$A, 0, [int]$B, [int]$C, $true) | Out-Null }
  'shot' {
    try { Front; Start-Sleep -Milliseconds 500 } catch {}
    $bnd = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    $bmp = New-Object System.Drawing.Bitmap $bnd.Width, $bnd.Height
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen($bnd.Location, [System.Drawing.Point]::Empty, $bnd.Size)
    $bmp.Save($A, [System.Drawing.Imaging.ImageFormat]::Png); $g.Dispose(); $bmp.Dispose()
    $fg = ([PZUi4]::GetForegroundWindow() -eq (W3).MainWindowHandle)
    "war3 foreground=$fg"
  }
  'click' { Front; [PZUi4]::SetCursorPos([int]$A, [int]$B) | Out-Null; Start-Sleep -Milliseconds 150; [PZUi4]::mouse_event(2,0,0,0,[IntPtr]::Zero); Start-Sleep -Milliseconds 60; [PZUi4]::mouse_event(4,0,0,0,[IntPtr]::Zero) }
  'wclick' { Front; [PZUi4]::SetCursorPos([int]([double]$A/1.25), [int]([double]$B/1.25)) | Out-Null; Start-Sleep -Milliseconds 250; [PZUi4]::mouse_event(2,0,0,0,[IntPtr]::Zero); Start-Sleep -Milliseconds 80; [PZUi4]::mouse_event(4,0,0,0,[IntPtr]::Zero) }
  'wheel' { Front; [PZUi4]::SetCursorPos([int]$A, [int]$B) | Out-Null; Start-Sleep -Milliseconds 200; for ($i=0; $i -lt [int]$C; $i++) { [PZUi4]::mouse_event(0x0800,0,0,120,[IntPtr]::Zero); Start-Sleep -Milliseconds 120 } }
  'rclick' { Front; [PZUi4]::SetCursorPos([int]$A, [int]$B) | Out-Null; Start-Sleep -Milliseconds 150; [PZUi4]::mouse_event(8,0,0,0,[IntPtr]::Zero); Start-Sleep -Milliseconds 60; [PZUi4]::mouse_event(16,0,0,0,[IntPtr]::Zero) }
  'key' { Front; [PZUi4]::keybd_event([byte][int]$A,0,0,[IntPtr]::Zero); Start-Sleep -Milliseconds 50; [PZUi4]::keybd_event([byte][int]$A,0,2,[IntPtr]::Zero) }
  'text' { Front; [System.Windows.Forms.SendKeys]::SendWait($A) }
}
