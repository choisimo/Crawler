## 스크립트 주요 기능 (linux_setup.sh)
### 명령줄 인자 지원

    -n, --non-interactive: 대화형 프롬프트 없이 실행

    -b, --browser TYPE: 브라우저 유형 지정 (chrome, firefox, both)

    -p, --packages LEVEL: 패키지 설치 수준 지정 (basic, extended, custom:패키지1,패키지2)

    -h, --headless: 헤드리스 모드 활성화

    --help: 도움말 표시


- 헤드리스 환경 지원

- Xvfb 가상 디스플레이 설치 및 구성

- 리눅스 서비스로 자동 시작 설정

- DISPLAY 환경 변수 자동 설정

- 다양한 환경 감지 및 설정

- Ubuntu/Debian, CentOS/RHEL, macOS, Windows 지원

- 적절한 패키지 매니저 자동 감지 및 사용

- 설정 파일을 통한 환경 구성 사용자 정의

- 브라우저 및 드라이버 버전 자동 매칭

- 기본, 확장, 사용자 정의 패키지 설치 옵션

- 로그 및 오류 처리

- 자세한 타임스탬프 포함 로그 생성

- 모든 작업의 단계별 진행 상황 표시

- 샘플 스크립트 생성

- 기본 웹 자동화 예제 스크립트

- 헤드리스 모드 테스트 스크립트

## example installation configuartion
```bash
# 비대화형 모드로 설치 (모든 질문에 기본값 사용)
./selenium_setup.sh --non-interactive

# 특정 브라우저만 설치
./selenium_setup.sh --browser firefox

# 확장 패키지 설치
./selenium_setup.sh --packages extended

# 헤드리스 모드 활성화 (GUI 없는 환경용)
./selenium_setup.sh --headless

# 여러 옵션 조합
./selenium_setup.sh --non-interactive --browser both --packages extended --headless
```

## default directory
```bash
프로젝트 폴더/
  ├── drivers/            # 브라우저 드라이버 파일
  ├── logs/               # 실행 로그 파일
  ├── results/            # 자동화 실행 결과
  ├── screenshots/        # 스크린샷
  ├── venv/               # Python 가상 환경
  ├── selenium_setup.conf # 설정 파일
  ├── web_automation.py   # 기본 자동화 샘플 스크립트
  └── test_headless.py    # 헤드리스 모드 테스트 스크립트
```