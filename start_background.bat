@echo off
cd /d "%~dp0"
echo Starting SecureDocs & Cloudflare Tunnel permanently in Windows background...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$py = '\"C:\Users\MY PC\AppData\Local\Programs\Python\Python313\pythonw.exe\" \"%~dp0run.py\"'; Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine = $py; CurrentDirectory = '%~dp0'} | Out-Null; Start-Sleep -Seconds 2; $cf = 'powershell.exe -NoProfile -Command \"Set-Location ''%~dp0''; .\cloudflared.exe tunnel --url http://127.0.0.1:5000 *>&1 | Out-File -FilePath ''%~dp0tunnel.log'' -Encoding utf8\"'; Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine = $cf; CurrentDirectory = '%~dp0'} | Out-Null"
echo.
echo ========================================================
echo SecureDocs is running in the background!
echo Local Link: http://localhost:5000
echo Check tunnel.log for the public HTTPS link!
echo ========================================================
echo.
timeout /t 4 >nul
