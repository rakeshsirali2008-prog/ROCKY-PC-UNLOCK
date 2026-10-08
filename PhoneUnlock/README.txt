PHONE UNLOCK  (Android biometric -> Windows lock screen, over Wi-Fi or phone hotspot)

NOT TESTED - first build, may need small fixes.

=== 1. Build the APK ===
1. Install Android Studio. Open the "android" folder (File > Open).
2. Wait for Gradle sync (needs internet the first time).
3. Build > Build Bundle(s)/APK(s) > Build APK(s).
4. APK: android/app/build/outputs/apk/debug/app-debug.apk
5. Copy to phone, install (allow "unknown sources").

=== 2. Set up the PC ===
1. Install Python from python.org (tick "Add python.exe to PATH").
2. Download PsExec (Microsoft Sysinternals), put psexec.exe inside the "pc" folder.
3. Edit pc/config.json:  "secret" = any long text you invent,
   "password" = your Windows PIN or password.
4. Run pc/setup_firewall.bat as administrator (once).
5. Make the Wi-Fi network "Private" in Windows settings.
6. Run pc/start_server.bat as administrator. Leave the window open.
   It prints the PC's IP address(es).

=== 3. Connect ===
- Same Wi-Fi: put phone and PC on the same network, OR
- Hotspot: turn on phone hotspot, connect the PC to it, run start_server.bat, use the IP it prints.
In the app: enter PC IP + the same secret, tap "Unlock PC", use fingerprint/face.
Lock the PC (Win+L) and test.

=== Notes ===
- It only types when the PC is on the lock screen, so pressing it while unlocked does nothing.
- After a reboot, log in once and run start_server.bat again.
- Phone and PC clocks must be within 60 seconds.
- If your PC uses a Microsoft account password, put that password in config.json.
