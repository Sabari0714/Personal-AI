[app]
# ROLEX AI — Android build configuration
title = ROLEX AI
package.name = rolexai
package.domain = org.rolexai

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,txt,md,csv,ttf,otf
source.exclude_dirs = tests,bin,.git,__pycache__,data/backups,logs,build
source.exclude_patterns = .env,*.db,*.db-wal,*.db-shm,*.apk

version = 1.0.0

# Requirements — validated against python-for-android / NDK combination
requirements = python3,kivy,pyjnius,android,plyer,requests,urllib3,chardet,idna,certifi

# Optional heavy deps (enable only if needed and validated):
# requirements = python3,kivy,pyjnius,android,plyer,pillow,openpyxl,pypdf

orientation = portrait
fullscreen = 0

# Android API levels
android.api = 34
android.minapi = 23
android.ndk_api = 23
android.archs = arm64-v8a

# Pin python-for-android to a stable release (avoids Python 3.14 / NDK r28
# build regressions present in the default 'develop' branch).
p4a.branch = v2024.01.21
# Known-good NDK for p4a v2024.01.21
android.ndk = 25b

# Permissions
android.permissions = INTERNET,RECORD_AUDIO,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,VIBRATE,WAKE_LOCK

android.allow_backup = True
android.accept_sdk_license = True

# App metadata
android.apptheme = @android:style/Theme.NoTitleBar
android.presplash_color = #0B0E14

# Logging
log_level = 2

# Icon (512x512 png at assets/icon.png)
icon.filename = %(source.dir)s/assets/icon.png

# Presplash (boot screen image)
presplash.filename = %(source.dir)s/assets/presplash.png

[buildozer]
log_level = 2
warn_on_root = 0
