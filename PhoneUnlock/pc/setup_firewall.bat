@echo off
REM Right-click -> Run as administrator (one time)
netsh advfirewall firewall add rule name="PhoneUnlock" dir=in action=allow protocol=TCP localport=8765 profile=any
pause
