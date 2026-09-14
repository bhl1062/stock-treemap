# 내 주식 트리맵 (Android / Kivy / 네이버 금융)

보유 종목의 종목코드·매수단가·매수수량을 휴대폰에 입력해두면, 네이버 금융에서
시세를 가져와 **평가금액 비중 = 사각형 크기, 매수가 대비 수익률 = 색상**
(빨강=수익, 파랑=손실 — 국내 증시 관례)으로 트리맵을 그려주는 안드로이드 앱입니다.

## 파일 구성

| 파일 | 설명 |
|---|---|
| `main.py` | Kivy 앱 본체 (화면 UI, 새로고침 로직) |
| `naver_api.py` | 네이버 금융에서 시세를 가져오는 모듈 |
| `portfolio.py` | 보유 종목을 로컬 JSON 파일로 저장/관리 |
| `treemap_widget.py` | 트리맵 레이아웃 계산 + Kivy 캔버스 렌더링 |
| `test_naver_api.py` | 시세 조회 모듈만 따로 테스트하는 스크립트 |
| `buildozer.spec` | 안드로이드 APK 빌드 설정 |
| `requirements.txt` | 데스크톱 테스트용 파이썬 패키지 목록 |

## 1) 먼저 데스크톱(PC)에서 테스트하기

APK를 빌드하기 전에, 본인 PC(Windows/Mac/Linux)에서 먼저 정상 동작하는지
확인하는 것을 강력히 권장합니다.

```bash
pip install -r requirements.txt

# 1. 시세 조회 모듈만 단독 테스트 (본인 PC/네트워크 환경에서 실행하세요)
python test_naver_api.py 005930 000660

# 2. 앱 전체 실행 (창이 뜨고 데스크톱에서도 동일하게 동작합니다)
python main.py
```

> ⚠️ 이 코드는 네이버의 **공식 API가 아니라 공개 웹페이지를 파싱**하는 방식입니다.
> 네이버가 페이지 구조를 바꾸면 `naver_api.py`의 CSS 셀렉터(`no_today`,
> `no_exday`, `blind` 등)를 최신 구조에 맞게 수정해야 할 수 있습니다.
> (이 작업을 수행한 개발 환경은 보안 정책상 finance.naver.com 접속 자체가
> 차단되어 있어, 실제 응답으로 100% 검증하지 못한 상태로 제공합니다. 최근
> 몇 년간 널리 쓰여온 안정적인 구조를 기반으로 작성했지만, 꼭 위 테스트로
> 먼저 확인해 주세요.)
>
> 더 안정적인 방법을 원한다면 한국투자증권 OpenAPI, 키움증권 OpenAPI 등
> **공식 증권사 API**(무료 발급)로 교체하는 것도 고려해 보세요. `naver_api.py`의
> `fetch_quote(code)` 함수 하나만 그대로 유지하면 나머지 코드(포트폴리오,
> 트리맵)는 수정 없이 재사용할 수 있습니다.

## 2) 안드로이드 APK로 빌드하기 (buildozer)

buildozer는 **Linux(또는 WSL) 환경**에서 가장 안정적으로 동작합니다.
(Mac도 가능하지만 Linux를 권장합니다. Windows는 WSL2 Ubuntu 사용 권장.)

```bash
# Ubuntu/Debian 기준 필요한 시스템 패키지
sudo apt update
sudo apt install -y python3-pip build-essential git ffmpeg libsdl2-dev \
    libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev libportmidi-dev \
    libswscale-dev libavformat-dev libavcodec-dev zlib1g-dev unzip openjdk-17-jdk

pip3 install --upgrade buildozer cython

cd stock_treemap_app
buildozer -v android debug
```

- 처음 빌드할 때 Android SDK/NDK를 자동으로 다운로드하므로 시간이 꽤 걸립니다
  (환경에 따라 20분~1시간+).
- 빌드가 끝나면 `bin/stocktreemap-0.1-arm64-v8a_armeabi-v7a-debug.apk` 파일이
  생성됩니다.

### 휴대폰에 설치하기

```bash
# USB 디버깅을 켠 안드로이드 폰을 PC에 연결한 상태에서
adb install bin/stocktreemap-0.1-*-debug.apk
```

또는 생성된 `.apk` 파일을 휴대폰으로 전송(카카오톡 나에게 보내기, 이메일,
구글 드라이브 등)한 뒤 파일 탐색기에서 직접 눌러 설치해도 됩니다.
("출처를 알 수 없는 앱 설치 허용" 권한이 필요할 수 있습니다.)

## 3) 앱 사용법

1. 첫 화면(보유 종목 관리)에서 종목코드(네이버 금융 기준 6자리 숫자, 예:
   삼성전자=005930, SK하이닉스=000660), 매수단가, 매수수량을 입력하고 [추가].
2. [트리맵 보기]를 누르면 자동으로 네이버에서 현재가를 조회해 트리맵을 그립니다.
3. [새로고침]으로 수동 갱신, [자동새로고침 ON]으로 30초마다 자동 갱신할 수
   있습니다. (`main.py`의 `AUTO_REFRESH_SECONDS` 값을 바꾸면 주기를 조절할
   수 있습니다.)
4. 사각형 크기 = 평가금액(현재가 × 수량) 비중, 색상 = 매수가 대비 수익률
   (빨강 진할수록 수익, 파랑 진할수록 손실).

## 4) 참고 — 종목코드 찾는 법

네이버 금융(https://finance.naver.com)에서 종목을 검색하면 주소창의
`code=` 뒤에 나오는 6자리 숫자가 종목코드입니다.
(해외 주식은 이 앱에서 기본 지원하지 않습니다. 국내 상장 종목 기준입니다.)

## 5) 알려진 제한사항

- "실시간"이라기보다는 **새로고침을 누른 시점의 최신 시세**를 가져오는
  방식입니다(웹소켓 실시간 스트리밍이 아닌 요청/응답 방식).
- 네이버 페이지가 응답하지 않거나 구조가 바뀌면 자동으로 최근 종가 기준
  백업 API로 대체되며, 그마저 실패하면 매수단가를 그대로 표시합니다.
- 배당금, 환율(해외주식), 세금은 계산에 포함되어 있지 않습니다.
