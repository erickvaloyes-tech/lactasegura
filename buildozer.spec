# (buildozer) buildozer.spec for LactaSegura
# Auto-generated minimal configuration. Review and adapt package.domain and version.
[app]
title = LactaSegura
package.name = LactaSegura
package.domain = org.example
source.dir = .
source.include_exts = py,kv,json,png,jpg,txt
version = 0.1
requirements = python3,kivy==2.3.1,requests,plyer,kivy_garden.graph
orientation = portrait
fullscreen = 0
presplash.filename =
icon.filename =

[buildozer]
log_level = 2
warn_on_root = 1

[app_android]
# Minimum API to support (adjustable)
android.api = 31
android.minapi = 21
android.ndk = 25b
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

[title]
# leave empty: handled above
