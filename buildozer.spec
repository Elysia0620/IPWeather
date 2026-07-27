[app]
title = IP天气追踪器
package.name = ipweather
package.domain = org.test
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 0.1
# json 是 Python 自带的，不需要写
# 但 requests、certifi 等第三方库必须写
requirements = python3,kivy,openssl,requests,urllib3,chardet,idna,certifi
orientation = portrait
fullscreen = 0
android.permissions = INTERNET
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
