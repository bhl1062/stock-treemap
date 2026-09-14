[app]
title = 내주식트리맵
package.name = stocktreemap
package.domain = org.example

source.dir = .
source.include_exts = py,png,jpg,kv,atlas

version = 0.1

# python-for-android가 빌드할 때 pip으로 설치할 패키지들
requirements = python3,kivy==2.3.0,requests,beautifulsoup4,certifi,urllib3,idna,charset-normalizer,soupsieve

orientation = portrait
fullscreen = 0

# 인터넷 접근 권한 (네이버에서 시세를 가져오기 위해 필수)
android.permissions = INTERNET

android.api = 33
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a

[buildozer]
log_level = 2
warn_on_root = 1
