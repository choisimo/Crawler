# Selenium 딸깍기 ver0.01 - 귀찮음 해결 매크로 생성기 

웹 브라우저 자동화 도구인 Selenium을 활용한 웹 자동화 환경을 위한 프로젝트

 Linux 환경을 기반으로 셸 스크립트를 통해 환경을 자동 구성하고, JSON 형식의 설정 파일을 이용하여 웹 크롤링 및 자동화 작업을 효율적으로 수행하는 방법을 사용함.
<hr/>

## 목차
- [설치 인터페이스](#header-1)
- [설치 및 사용방법](#header-2)
- [명령줄 옵션](#header-3)
- [Gemini API 통합 사용](#header-4)
- [주요 기능 설명](#header-5)
- [문제 해결 트러블 슈팅 해결방법](#header-6)

<a id="header-1"></a>
## 개발 및 테스트 환경
```bash
우분투 서버 24.04 LTS
```

<br/>
<br/>

<a id="header-2"></a>
## 설치 및 간략한 사용방법 (전체 옵션 설명 안 함)

```bash
# root/configuration 내부의 shellscript 파일
# > 실행 권한 없으면 chmod +x 으로 권한 주기
chmod +x ./setup.sh
```

### 설치 (옵션 별로 상이함)
```bash
# 기본 설치 (Chrome 브라우저, 기본 패키지)
./setup.sh

# 헤드리스 모드로 Firefox 브라우저 설치
./setup.sh --browser firefox --headless

# Gemini API 통합 및 자동 설정 생성
./setup.sh --gemini --gemini-task "네이버에서 '맛집' 검색 후 결과 스크린샷 저장" --gemini-output "naver_search.json"

# 모든 옵션 사용 예시
./setup.sh --non-interactive --browser both --packages extended --headless --gemini
```

### 설치 완료 후 가상환경 활성화
```bash
## shellscript (셋업 전용) 과 동일한 디렉토리에 존재
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate    # Windows
```

### 스크립트 실행하기 (파이썬 가상환경에서 실행)
```bash
python web_automation.py
```

<a id="header-3"></a>
## 명령줄 옵션

### 기본 옵션
| 플래그 | 설명 | 기본값 | 예시 |
| --- | --- | --- | --- |
| -n, --non-interactive | 대화형 프롬프트 없이 실행 | false | --non-interactive |
| -b, --browser TYPE | 브라우저 유형 (chrome, firefox, both) | chrome | --browser firefox |
| -p, --packages LEVEL | 패키지 레벨 (basic, extended, custom:패키지1,패키지2) | basic | --packages extended |
| -h, --headless | 헤드리스 브라우저 모드 설정 | false | --headless |
| --help | 도움말 메시지 표시 | - | --help |
<hr/>

### Gemini api 적용 옵션
| 플래그 | 설명 | 기본값 | 예시 |
| --- | --- | --- | --- |
| --gemini | Gemini API 통합 설치 | - | --gemini |
| --gemini-api-key | Gemini API 키 설정 | - | --gemini-api-key "YOUR_API_KEY" |
| --gemini-task | Gemini 작업 설명 (이 설정 시 Gemini 활성화) | - | --gemini-task "네이버 검색 자동화" |
| --gemini-output | Gemini 설정 출력 파일 경로 | - | --gemini-output "config.json" |
<hr/>

<br/>

<a id="header-4"></a>
## Gemini API 통합 사용

### 통합 설치 방법
```bash
# installation
./setup.sh --gemini 
/bin/bash --gemini
```

### API key 설정 방법
#### 1. .env 파일 이용한 방식
```bash
# .env 파일 위치
sudo mkdir -p ../gemini/.env
# .env 파일 내용
GEMINI_API_KEY=your_api_key
```
#### 2. 직접 옵션으로 지정
```bash
--gemini-api-key "your_api_key"
```

### 설정 파일 생성하기 (default config 파일 검증 횟수 : 5)
```bash
./setup.sh --gemini --gemini-task "네이버에서 '코로나 바이러스' 검색 후 결과 저장" --gemini-output "naver_search_config.json"
```
### 직접 파이썬 실행해서 생성하기
```bash
python ./gemini_config_gen.py --task "네이버에서 '코로나 바이러스' 검색 후 결과 저장" 
--output "naver_search_config.json"
```

### 사용자 지정 프롬프트 사용하기
```bash
# 프롬프트를 파일로 저장
echo "여기에 사용자 정의 프롬프트 작성" > custom_prompt.txt

# 저장한 프롬프트 파일 사용
python gemini_config_gen.py --task "구글에서 '파이썬 튜토리얼' 검색" --prompt custom_prompt.txt
```

<a id="header-5"></a>

### 1. ./setup.sh --help 으로 확인

```bash
===== Selenium 웹 자동화 환경 설정 =====
[INFO] [2025-04-15 11:06:24] 로깅 시작: logs/setup_20250415_110624.log
사용법: ./linux_setup.sh [옵션]
옵션:
  -n, --non-interactive   대화형 프롬프트 없이 실행
  -b, --browser TYPE      브라우저 유형 (chrome, firefox, both)
  -p, --packages LEVEL    패키지 레벨 (basic, extended, custom:패키지1,패키지2)
  -h, --headless          헤드리스 브라우저 모드 설정
  --help                  이 도움말 메시지 표시
```

### 2. python ./gemini_config_gen.py --help 으로 확인

```bash
usage: gemini_config_gen.py [-h] --task TASK [--output OUTPUT] [--api-key API_KEY] [--max-retries MAX_RETRIES] [--validate-only]

Gemini API를 이용한 Selenium 설정 파일 생성

options:
  -h, --help            show this help message and exit
  --task TASK           자동화 작업 설명
  --output OUTPUT       출력 파일 경로
  --api-key API_KEY     Gemini API 키
  --max-retries MAX_RETRIES
                        최대 시도 횟수
  --validate-only       기존 설정 파일만 검증
```

<hr/>

<a id="header-6"></a>
### 일단 생략

<hr/>
