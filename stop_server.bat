@echo off
echo ========================================================
echo             Stopping SecureDocs Server & Tunnel
echo ========================================================
echo.
powershell -NoProfile -ExecutionPolicy Bypass -Command "$procs = Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique; if ($procs) { foreach ($p in $procs) { Stop-Process -Id $p -Force; Write-Host 'Stopped SecureDocs server process' $p } } else { Write-Host 'No SecureDocs server was running on port 5000.' }; Stop-Process -Name 'cloudflared' -Force -ErrorAction SilentlyContinue; Write-Host 'Stopped Cloudflare Tunnel.'"
echo.
echo Done.
pause
