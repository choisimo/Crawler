# Selenium 딸깍기 ver0.01 - 귀찮음 해결 매크로 생성기 

## 1. 서론

본 보고서는 웹 브라우저 자동화 도구인 Selenium을 활용한 웹 자동화 환경 구축 및 구현 방법에 관한 내용을 다룬다. Linux 환경을 기반으로 셸 스크립트를 통해 환경을 자동 구성하고, JSON 형식의 설정 파일을 이용하여 웹 크롤링 및 자동화 작업을 효율적으로 수행하는 방법을 제시한다.

## 2. 환경 구성 방법론

### 2.1 기본 요구사항

- 운영체제: Linux 계열(Ubuntu 18.04 이상 권장)

### 2.2 설치 프로세스

다음 과정을 통해 셸 스크립트를 실행하여 환경을 구성한다:

```bash
# 스크립트 파일 복사
cp configuration/linux_setup.sh /대상/디렉토리/

# 실행 권한 부여
chmod +x ./linux_setup.sh

# 스크립트 실행
sudo /bin/bash ./linux_setup.sh
```

### 2.3 구성 요소 분석

스크립트 실행 시 다음과 같은 작업이 수행된다:

1. 시스템 의존성 패키지 설치(wget, unzip, python3 관련 패키지)
2. Python 가상 환경 구성 및 활성화
3. Selenium 패키지 및 관련 라이브러리 설치
4. 브라우저 버전 감지 및 호환 드라이버 자동 설치
5. 기본 자동화 스크립트 생성
6. 환경 변수 및 경로 설정

설치 완료 후에는 다음과 같은 디렉토리 구조가 생성된다:

```
프로젝트_디렉토리/
├── drivers/               # 브라우저 드라이버 실행 파일
├── logs/                  # 실행 로그 파일 저장소
├── results/               # 추출 데이터 저장소
├── screenshots/           # 캡처 이미지 저장소
├── venv/                  # Python 가상 환경
├── selenium_setup.conf    # 환경 설정 파일
├── test_headless.py       # 테스트용 스크립트
└── web_automation.py      # 메인 자동화 스크립트
```

## 3. 가상 환경 활성화 절차

Selenium 스크립트를 실행하기 위해서는 다음과 같이 가상 환경을 활성화해야 한다:

```bash
source venv/bin/activate
```

가상 환경 활성화 시 터미널 프롬프트에 `(venv)` 접두사가 표시되는 것을 확인할 수 있다.

## 4. 설정 파일 구조 분석

### 4.1 JSON 형식 설정 파일 스키마

웹 자동화 작업은 `config.json` 파일을 통해 정의되며, 다음과 같은 구조로 구성된다:

```json
{
  "browser": {
    "type": "chrome",
    "headless": true,
    "options": [
      "--no-sandbox",
      "--disable-dev-shm-usage",
      "--window-size=1920,1080",
      "--lang=ko_KR"
    ]
  },
  "targets": [
    {
      "name": "대상사이트",
      "url": "https://example.com",
      "wait_for": {
        "type": "css",
        "value": "element_selector",
        "timeout": 10
      },
      "actions": [
        {
          "type": "screenshot",
          "filename": "initial_page.png"
        },
        {
          "type": "input",
          "selector": {
            "type": "id",
            "value": "search_input"
          },
          "text": "검색어",
          "submit": false
        },
        {
          "type": "click",
          "selector": {
            "type": "css",
            "value": "button.search"
          }
        },
        {
          "type": "wait",
          "seconds": 3
        },
        {
          "type": "extract",
          "selector": {
            "type": "css",
            "value": "result_items"
          },
          "save": true,
          "output_file": "results.txt"
        }
      ]
    }
  ],
  "output": {
    "log_level": "INFO",
    "results_dir": "results",
    "screenshots_dir": "screenshots",
    "logs_dir": "logs"
  },
  "timeouts": {
    "default_wait": 10,
    "page_load": 30
  }
}
```

### 4.2 주요 설정 항목 분석

본 설정 파일은 다음과 같은 주요 섹션으로 구성된다:

- **browser**: 브라우저 유형, 헤드리스 모드 여부, 브라우저 옵션 정의
- **targets**: 자동화 대상 웹사이트 및 작업 순서 정의
- **actions**: 순차적 실행 작업 정의(스크린샷, 입력, 클릭, 대기, 데이터 추출 등)
- **output**: 출력 파일 경로 및 로그 레벨 설정
- **timeouts**: 기본 대기 시간 및 페이지 로드 타임아웃 설정

## 5. 실행 방법론

### 5.1 기본 실행 명령

설정 파일을 이용하여 다음과 같이 자동화 스크립트를 실행한다:

```bash
python web_automation.py --config config.json
```

### 5.2 고급 실행 옵션 적용

다음과 같은 옵션을 사용하여 실행을 세분화할 수 있다:

```bash
# 특정 대상만 선택적 실행
python web_automation.py --config config.json --target "대상사이트명"

# 헤드리스 모드 강제 적용
python web_automation.py --config config.json --headless

# 복합 옵션 적용
python web_automation.py --config config.json --target "대상사이트명" --headless
```

### 5.3 환경 검증 방법

환경 설정이 정상적으로 완료되었는지 확인하기 위해 다음 명령을 실행한다:

```bash
python test_headless.py
```

## 6. 문제 해결 방안

### 6.1 일반적 오류 해결 방법

자주 발생하는 오류와 해결 방법은 다음과 같다:

| 오류 유형 | 해결 방안 |
|---------|---------|
| 드라이버 실행 권한 오류 | `chmod +x drivers/*` 명령으로 실행 권한 부여 |
| 헤드리스 모드 렌더링 오류 | `export DISPLAY=:99` 환경 변수 설정으로 가상 디스플레이 지정 |
| 세션 생성 실패 오류 | `pkill -f chrome` 명령으로 잔여 프로세스 정리 |
| 요소 탐색 실패 | 타임아웃 값 증가 또는 셀렉터 다시 확인 후 수정 |

### 6.2 트러블 슈팅 - 세션 충돌

Chrome 브라우저의 세션 충돌 문제는 다음과 같이 임시 프로필 설정으로 해결할 수 있다:

```json
"options": [
  "--no-sandbox",
  "--disable-dev-shm-usage",
  "--incognito",
  "--user-data-dir=/tmp/chrome-data-temp"
]
```

## 7. 개선 방향

- 

## 8. 마무리하며

본 보고서에서는 Selenium을 활용한 웹 자동화 환경 구축 및 구현 방법을 체계적으로 분석하였다. `linux_setup.sh` 스크립트를 통한 환경 구성과 `config.json` 파일을 활용한 자동화 작업 정의는 반복적인 웹 작업을 효율적으로 자동화할 수 있는 방법이다.
