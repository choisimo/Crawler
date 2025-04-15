#!/bin/bash
#
# Selenium 웹 자동화 환경 설정 스크립트
# 헤드리스 리눅스 환경에서도 사용 가능하도록 설계됨
#

# 색상 코드 설정
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# 기본 설정값
NON_INTERACTIVE=false
BROWSER_TYPE="chrome"
PACKAGE_LEVEL="basic"
HEADLESS_MODE=false
DRIVER_VERSION_CHROME="latest"
DRIVER_VERSION_FIREFOX="latest"
PYTHON_VERSION=3

# 로깅 함수
log_success() { 
  local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
  echo -e "${GREEN}[SUCCESS]${NC} [$timestamp] $1"
}

log_info() { 
  local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
  echo -e "${YELLOW}[INFO]${NC} [$timestamp] $1"
}

log_error() { 
  local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
  echo -e "${RED}[ERROR]${NC} [$timestamp] $1"
}

# 도움말 표시 함수
function show_help {
  echo "사용법: $0 [옵션]"
  echo "옵션:"
  echo "  -n, --non-interactive   대화형 프롬프트 없이 실행"
  echo "  -b, --browser TYPE      브라우저 유형 (chrome, firefox, both)"
  echo "  -p, --packages LEVEL    패키지 레벨 (basic, extended, custom:패키지1,패키지2)"
  echo "  -h, --headless          헤드리스 브라우저 모드 설정"
  echo "  --help                  이 도움말 메시지 표시"
  exit 0
}

# 명령줄 인자 처리 함수
parse_arguments() {
  while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
      -n|--non-interactive)
        NON_INTERACTIVE=true
        shift
        ;;
      -b|--browser)
        BROWSER_TYPE="$2"
        shift 2
        ;;
      -p|--packages)
        PACKAGE_LEVEL="$2"
        shift 2
        ;;
      -h|--headless)
        HEADLESS_MODE=true
        shift
        ;;
      --help)
        show_help
        ;;
      *)
        echo "알 수 없는 옵션: $1"
        show_help
        ;;
    esac
  done
}

# 로깅 설정 함수
setup_logging() {
  LOG_DIR="logs"
  LOG_FILE="$LOG_DIR/setup_$(date +%Y%m%d_%H%M%S).log"
  
  mkdir -p "$LOG_DIR"
  touch "$LOG_FILE"
  
  # 표준 출력과 로그 파일에 모두 출력
  exec > >(tee -a "$LOG_FILE")
  exec 2>&1
  
  log_info "로깅 시작: $LOG_FILE"
}

# 설정 파일 처리 함수
load_config() {
  CONFIG_FILE="./selenium_setup.conf"
  
  if [ -f "$CONFIG_FILE" ]; then
    log_info "설정 파일 로드 중: $CONFIG_FILE"
    source "$CONFIG_FILE"
    log_success "설정 파일 로드 완료"
  else
    log_info "설정 파일을 찾을 수 없습니다. 기본값을 사용합니다."
    
    # 설정 파일 생성 (향후 사용을 위해)
    cat > "$CONFIG_FILE" << EOF
# Selenium 설정 파일
BROWSER_TYPE=chrome
PACKAGE_LEVEL=basic
HEADLESS_MODE=false
DRIVER_VERSION_CHROME=latest
DRIVER_VERSION_FIREFOX=latest
PYTHON_VERSION=3
EOF
    log_info "기본 설정 파일이 생성되었습니다: $CONFIG_FILE"
  fi
}

# 디렉토리 생성 함수
create_directories() {
  log_info "작업 디렉토리 생성 중..."
  
  mkdir -p drivers results logs screenshots
  
  log_success "디렉토리 생성 완료"
}

# 운영체제 확인 및 필요한 소프트웨어 설치 함수
setup_environment() {
  log_info "운영체제 확인 및 필요한 소프트웨어 설치 중..."
  
  if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    log_info "Linux 운영체제 감지됨"
    
    # 패키지 매니저 확인
    if command -v apt-get &> /dev/null; then
      log_info "apt 패키지 매니저 사용"
      sudo apt-get update
      sudo apt-get install -y wget unzip python3 python3-pip python3-venv
      
      # 브라우저 설치 확인 및 설치
      if [[ "$BROWSER_TYPE" == "chrome" || "$BROWSER_TYPE" == "both" ]] && ! command -v google-chrome &> /dev/null; then
        log_info "Chrome 브라우저 설치 중..."
        wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
        echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
        sudo apt-get update
        sudo apt-get install -y google-chrome-stable
        log_success "Chrome 브라우저 설치 완료"
      fi
      
      if [[ "$BROWSER_TYPE" == "firefox" || "$BROWSER_TYPE" == "both" ]] && ! command -v firefox &> /dev/null; then
        log_info "Firefox 브라우저 설치 중..."
        sudo apt-get install -y firefox
        log_success "Firefox 브라우저 설치 완료"
      fi
    elif command -v yum &> /dev/null; then
      log_info "yum 패키지 매니저 사용"
      sudo yum update -y
      sudo yum install -y wget unzip python3 python3-pip
      
      if [[ "$BROWSER_TYPE" == "chrome" || "$BROWSER_TYPE" == "both" ]] && ! command -v google-chrome &> /dev/null; then
        log_info "Chrome 브라우저 설치 중..."
        wget https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm
        sudo yum install -y ./google-chrome-stable_current_x86_64.rpm
        rm ./google-chrome-stable_current_x86_64.rpm
        log_success "Chrome 브라우저 설치 완료"
      fi
      
      if [[ "$BROWSER_TYPE" == "firefox" || "$BROWSER_TYPE" == "both" ]] && ! command -v firefox &> /dev/null; then
        log_info "Firefox 브라우저 설치 중..."
        sudo yum install -y firefox
        log_success "Firefox 브라우저 설치 완료"
      fi
    else
      log_error "지원되지 않는 패키지 매니저입니다."
      exit 1
    fi
  elif [[ "$OSTYPE" == "darwin"* ]]; then
    log_info "macOS 운영체제 감지됨"
    
    if ! command -v brew &> /dev/null; then
      log_info "Homebrew 설치 중..."
      /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    
    log_info "필수 소프트웨어 설치 중..."
    brew install python wget
    
    if [[ "$BROWSER_TYPE" == "chrome" || "$BROWSER_TYPE" == "both" ]] && ! command -v google-chrome &> /dev/null; then
      log_info "Chrome 브라우저 설치 중..."
      brew install --cask google-chrome
      log_success "Chrome 브라우저 설치 완료"
    fi
    
    if [[ "$BROWSER_TYPE" == "firefox" || "$BROWSER_TYPE" == "both" ]] && ! command -v firefox &> /dev/null; then
      log_info "Firefox 브라우저 설치 중..."
      brew install --cask firefox
      log_success "Firefox 브라우저 설치 완료"
    fi
  elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    log_info "Windows 운영체제 감지됨"
    log_info "Windows에서는 Python, Chrome, Firefox를 수동으로 설치해야 합니다."
    log_info "Python: https://www.python.org/downloads/"
    log_info "Chrome: https://www.google.com/chrome/"
    log_info "Firefox: https://www.mozilla.org/firefox/"
  else
    log_error "지원되지 않는 운영체제입니다: $OSTYPE"
    exit 1
  fi
  
  log_success "환경 설정 완료"
}

update_python_for_selenium_manager() {
  log_info "Selenium Manager 활용을 위한 Python 코드 수정 중..."
  
  if [ -f "web_automation.py" ]; then
    # 백업 생성
    cp web_automation.py web_automation.py.bak
    
    # setup_driver 함수 수정
    sed -i 's/driver_path = os.path.join("drivers", "chromedriver")/# driver_path = os.path.join("drivers", "chromedriver")/g' web_automation.py
    sed -i 's/service = ChromeService(executable_path=driver_path)/# service = ChromeService(executable_path=driver_path)/g' web_automation.py
    sed -i 's/return webdriver.Chrome(service=service, options=options)/return webdriver.Chrome(options=options)/g' web_automation.py
    
    # Firefox, Edge 드라이버도 동일하게 수정
    sed -i 's/service = FirefoxService(executable_path=driver_path)/# service = FirefoxService(executable_path=driver_path)/g' web_automation.py
    sed -i 's/return webdriver.Firefox(service=service, options=options)/return webdriver.Firefox(options=options)/g' web_automation.py
    
    sed -i 's/service = EdgeService(executable_path=driver_path)/# service = EdgeService(executable_path=driver_path)/g' web_automation.py
    sed -i 's/return webdriver.Edge(service=service, options=options)/return webdriver.Edge(options=options)/g' web_automation.py
    
    log_success "Python 코드가 수정되었습니다. 이제 Selenium Manager가 자동으로 드라이버를 관리합니다."
  else
    log_error "web_automation.py 파일을 찾을 수 없습니다."
  fi
  
  # test_headless.py 파일도 수정
  if [ -f "test_headless.py" ]; then
    cp test_headless.py test_headless.py.bak
    
    # 주석 처리된 서비스 코드와 직접 드라이버 지정 부분 제거
    awk '
    /# 크롬 드라이버 경로/{
      print "    # Selenium 4.6+ 자동 드라이버 관리 사용"
      print "    options = ChromeOptions()"
      print "    options.add_argument(\"--headless\")"
      print "    options.add_argument(\"--no-sandbox\")"
      print "    options.add_argument(\"--disable-dev-shm-usage\")"
      print "    options.add_argument(\"--window-size=1920,1080\")"
      print ""
      print "    # 디버그 정보 출력"
      print "    logger.info(f\"드라이버 옵션: {options.arguments}\")"
      print ""
      print "    # 웹드라이버 시작 (자동 드라이버 관리 사용)"
      print "    driver = webdriver.Chrome(options=options)"
      
      # 다음 "webdriver.Chrome" 호출 줄까지 건너뜀
      skip = 1
    }
    /driver = webdriver.Chrome/{
      if (skip) {
        skip = 0
        next
      }
    }
    {
      if (!skip) print
    }
    ' test_headless.py > test_headless.py.new
    
    mv test_headless.py.new test_headless.py
    chmod +x test_headless.py
    
    log_success "test_headless.py 파일이 수정되었습니다."
  fi
}


# 헤드리스 환경 의존성 설치 함수
install_headless_dependencies() {
  log_info "헤드리스 브라우저 의존성 설치 중..."
  
  if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # X 가상 프레임 버퍼 및 필수 라이브러리 설치
    if command -v apt-get &> /dev/null; then
      sudo apt-get update
      sudo apt-get install -y xvfb libxi6 libgconf-2-4 default-jdk
    elif command -v yum &> /dev/null; then
      sudo yum install -y xorg-x11-server-Xvfb libXi libX11 java-11-openjdk
    fi
    
    # Xvfb 서비스 설정
    cat > xvfb.service << EOF
[Unit]
Description=X Virtual Frame Buffer Service
After=network.target

[Service]
ExecStart=/usr/bin/Xvfb :99 -screen 0 1280x1024x24 -ac
ExecStartPre=/bin/bash -c "/usr/bin/pkill Xvfb || true"

[Install]
WantedBy=multi-user.target
EOF
    
    sudo mv xvfb.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable xvfb.service
    sudo systemctl start xvfb.service
    
    # 환경 변수 설정
    echo 'export DISPLAY=:99' >> ~/.bashrc
    export DISPLAY=:99
    
    log_success "헤드리스 브라우저 의존성 설치 완료"
  else
    log_info "현재 운영체제에서는 추가 헤드리스 의존성이 필요하지 않습니다."
  fi
}

# Python 가상 환경 설정 함수
setup_virtualenv() {
  log_info "Python 가상 환경 설정 중..."
  
  if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    python -m venv venv
    log_info "가상 환경을 활성화하려면 'venv\\Scripts\\activate' 명령어 실행"
  else
    python3 -m venv venv
    source venv/bin/activate
    log_info "Python 가상 환경 활성화됨"
  fi
  
  log_success "Python 가상 환경 설정 완료"
}

# Python 패키지 설치 함수
install_python_packages() {
  log_info "Python 패키지 설치 중..."
  
  if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    PYTHON_CMD="venv\\Scripts\\python"
    PIP_CMD="venv\\Scripts\\pip"
  else
    PYTHON_CMD="venv/bin/python"
    PIP_CMD="venv/bin/pip"
  fi
  
  $PIP_CMD install --upgrade pip
  
  # 기본 패키지 설치
  if [[ "$PACKAGE_LEVEL" == "basic" || "$PACKAGE_LEVEL" == "extended" ]]; then
    log_info "기본 Python 패키지 설치 중..."
    $PIP_CMD install selenium webdriver-manager
  fi
  
  # 확장 패키지 설치
  if [[ "$PACKAGE_LEVEL" == "extended" ]]; then
    log_info "확장 Python 패키지 설치 중..."
    $PIP_CMD install pytest pytest-selenium requests beautifulsoup4 pillow pandas
  fi
  
  # 사용자 지정 패키지 설치
  if [[ "$PACKAGE_LEVEL" == custom:* ]]; then
    CUSTOM_PACKAGES=${PACKAGE_LEVEL#custom:}
    IFS=',' read -ra PKG_ARRAY <<< "$CUSTOM_PACKAGES"
    log_info "사용자 지정 Python 패키지 설치 중: ${PKG_ARRAY[*]}"
    $PIP_CMD install "${PKG_ARRAY[@]}"
  fi
  
  log_success "Python 패키지 설치 완료"
}

# 브라우저 드라이버 설치 함수
install_browser_drivers() {
  log_info "브라우저 드라이버 설치 중..."
  
  mkdir -p drivers
  
  if [[ "$BROWSER_TYPE" == "chrome" || "$BROWSER_TYPE" == "both" ]]; then
    # Chrome 버전 확인
    if command -v google-chrome &> /dev/null; then
      CHROME_VERSION=$(google-chrome --version | awk '{print $3}')
      CHROME_MAJOR_VERSION=$(echo $CHROME_VERSION | cut -d '.' -f 1)
      log_info "감지된 Chrome 버전: $CHROME_VERSION (주 버전: $CHROME_MAJOR_VERSION)"
      
      # Chrome 115 이상 버전과 이전 버전의 다운로드 URL이 다름
      if [ "$CHROME_MAJOR_VERSION" -ge 115 ]; then
        log_info "Chrome 버전 115 이상 감지, 새로운 다운로드 방식 사용"
        CHROMEDRIVER_URL="https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/${CHROME_VERSION}/linux64/chromedriver-linux64.zip"
        
        wget -q -O drivers/chromedriver.zip "$CHROMEDRIVER_URL" || {
          log_error "Chrome 115+ 드라이버 다운로드 실패, 대체 URL 시도"
          # 정확한 버전이 없으면 최신 안정 버전 시도
          CHROMEDRIVER_URL="https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/LATEST_RELEASE_${CHROME_MAJOR_VERSION}/linux64/chromedriver-linux64.zip"
          wget -q -O drivers/chromedriver.zip "$CHROMEDRIVER_URL" || log_error "Chrome 드라이버 다운로드 실패"
        }
        
        if [ -f drivers/chromedriver.zip ]; then
          unzip -q -o drivers/chromedriver.zip -d drivers/
          # Chrome 115+ 버전은 압축 해제 시 폴더 구조가 다름
          if [ -d drivers/chromedriver-linux64 ]; then
            mv drivers/chromedriver-linux64/chromedriver drivers/
            rm -rf drivers/chromedriver-linux64
          fi
        fi
      else {
        # Chrome 115 미만 버전용 다운로드 (기존 방식)
        if [[ "$DRIVER_VERSION_CHROME" == "latest" ]]; then
          log_info "최신 Chrome 드라이버 다운로드 중..."
          CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_MAJOR_VERSION}")
        else
          CHROMEDRIVER_VERSION="$DRIVER_VERSION_CHROME"
        fi
        
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
          CHROMEDRIVER_URL="https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip"
        elif [[ "$OSTYPE" == "darwin"* ]]; then
          CHROMEDRIVER_URL="https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_mac64.zip"
        else
          CHROMEDRIVER_URL="https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_win32.zip"
        fi
        
        wget -q -O drivers/chromedriver.zip "$CHROMEDRIVER_URL"
        unzip -q -o drivers/chromedriver.zip -d drivers/
      }
      fi
      
      # 권한 설정 및 정리
      chmod +x drivers/chromedriver
      rm -f drivers/chromedriver.zip
      
      # 드라이버 버전 확인
      INSTALLED_VERSION=$(drivers/chromedriver --version | awk '{print $2}')
      log_success "Chrome 드라이버 설치 완료 (버전: $INSTALLED_VERSION)"
      
      # PATH에 드라이버 디렉토리 추가
      DRIVERS_ABS_PATH=$(realpath drivers)
      echo "export PATH=\$PATH:$DRIVERS_ABS_PATH" >> ~/.bashrc
      export PATH=$PATH:$DRIVERS_ABS_PATH
      log_info "PATH 환경변수에 드라이버 경로 추가: $DRIVERS_ABS_PATH"
    else
      log_error "Chrome 브라우저가 설치되어 있지 않습니다. 먼저 브라우저를 설치해주세요."
      install_chrome_browser
    fi
  fi
  
  # Firefox 드라이버 설치 코드 (기존과 동일)
  if [[ "$BROWSER_TYPE" == "firefox" || "$BROWSER_TYPE" == "both" ]]; then
    # Firefox 드라이버(Geckodriver) 다운로드
    if [[ "$DRIVER_VERSION_FIREFOX" == "latest" ]]; then
      GECKODRIVER_VERSION=$(curl -s https://api.github.com/repos/mozilla/geckodriver/releases/latest | grep tag_name | cut -d '"' -f 4)
    else
      GECKODRIVER_VERSION="$DRIVER_VERSION_FIREFOX"
    fi
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
      GECKODRIVER_URL="https://github.com/mozilla/geckodriver/releases/download/${GECKODRIVER_VERSION}/geckodriver-${GECKODRIVER_VERSION}-linux64.tar.gz"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
      GECKODRIVER_URL="https://github.com/mozilla/geckodriver/releases/download/${GECKODRIVER_VERSION}/geckodriver-${GECKODRIVER_VERSION}-macos.tar.gz"
    else
      GECKODRIVER_URL="https://github.com/mozilla/geckodriver/releases/download/${GECKODRIVER_VERSION}/geckodriver-${GECKODRIVER_VERSION}-win64.zip"
    fi
    
    wget -q -O drivers/geckodriver.tar.gz "$GECKODRIVER_URL"
    tar -xzf drivers/geckodriver.tar.gz -C drivers/
    chmod +x drivers/geckodriver
    rm drivers/geckodriver.tar.gz
    
    log_success "Firefox 드라이버 설치 완료 (버전: $GECKODRIVER_VERSION)"
  fi
  
  # 설치 확인
  verify_driver_installation
}

install_chrome_browser() {
  log_info "Chrome 브라우저 설치 중..."
  
  if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # 패키지 매니저 확인
    if command -v apt-get &> /dev/null; then
      log_info "apt 패키지 매니저 사용"
      wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
      echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
      sudo apt-get update
      sudo apt-get install -y google-chrome-stable
    elif command -v yum &> /dev/null; then
      log_info "yum 패키지 매니저 사용"
      wget https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm
      sudo yum install -y ./google-chrome-stable_current_x86_64.rpm
      rm ./google-chrome-stable_current_x86_64.rpm
    else
      log_error "지원되지 않는 패키지 매니저입니다."
      return 1
    fi
    
    if command -v google-chrome &> /dev/null; then
      CHROME_VERSION=$(google-chrome --version | awk '{print $3}')
      log_success "Chrome 브라우저 설치 완료 (버전: $CHROME_VERSION)"
      return 0
    else
      log_error "Chrome 브라우저 설치 실패"
      return 1
    fi
  elif [[ "$OSTYPE" == "darwin"* ]]; then
    if command -v brew &> /dev/null; then
      brew install --cask google-chrome
      log_success "Chrome 브라우저 설치 완료"
      return 0
    else
      log_error "Homebrew가 설치되어 있지 않습니다. 먼저 Homebrew를 설치해주세요."
      return 1
    fi
  else
    log_error "자동 설치가 지원되지 않는 운영체제입니다. 수동으로 Chrome을 설치해주세요."
    return 1
  fi
}


verify_driver_installation() {
  log_info "드라이버 설치 확인 중..."
  
  # 크롬 드라이버 확인
  if [[ "$BROWSER_TYPE" == "chrome" || "$BROWSER_TYPE" == "both" ]]; then
    if [ -f "drivers/chromedriver" ] && [ -x "drivers/chromedriver" ]; then
      CHROMEDRIVER_VERSION=$(drivers/chromedriver --version | awk '{print $2}')
      log_success "Chrome 드라이버 설치 확인 완료 (버전: $CHROMEDRIVER_VERSION)"
      
      # Python 코드에서 Selenium의 자동 드라이버 관리 사용을 위한 힌트 파일 생성
      echo "# 이 파일은 Selenium 자동 드라이버 관리를 위해 사용됩니다." > drivers/selenium_driver_hints.txt
      echo "CHROME_DRIVER_VERSION=$CHROMEDRIVER_VERSION" >> drivers/selenium_driver_hints.txt
      echo "CHROME_DRIVER_PATH=$(realpath drivers/chromedriver)" >> drivers/selenium_driver_hints.txt
    else
      log_error "Chrome 드라이버가 올바르게 설치되지 않았습니다."
      log_info "Selenium의 자동 드라이버 관리 기능 사용을 권장합니다."
      
      # Python 스크립트 수정 안내
      log_info "다음과 같이 web_automation.py 파일을 수정하세요:"
      echo '
def setup_driver(config):
    """설정에 따라 웹 드라이버 설정"""
    browser_config = config["browser"]
    browser_type = browser_config.get("type", "chrome").lower()
    headless = browser_config.get("headless", True)
    browser_options = browser_config.get("options", [])
    
    # 브라우저 별 옵션 설정
    if browser_type == "chrome":
        options = ChromeOptions()
        if headless:
            options.add_argument("--headless")
        for option in browser_options:
            options.add_argument(option)
        # 경로 지정 없이 Selenium Manager 사용
        return webdriver.Chrome(options=options)
      '
    fi
  fi
  
  # Firefox 드라이버 확인
  if [[ "$BROWSER_TYPE" == "firefox" || "$BROWSER_TYPE" == "both" ]]; then
    if [ -f "drivers/geckodriver" ] && [ -x "drivers/geckodriver" ]; then
      GECKODRIVER_VERSION=$(drivers/geckodriver --version | head -n1 | awk '{print $2}')
      log_success "Firefox 드라이버 설치 확인 완료 (버전: $GECKODRIVER_VERSION)"
    else
      log_error "Firefox 드라이버가 올바르게 설치되지 않았습니다."
    fi
  fi
}

# 샘플 스크립트 생성 함수
generate_sample_script() {
  log_info "샘플 스크립트 생성 중..."
  
  if [ "$NON_INTERACTIVE" = false ]; then
    read -p "샘플 스크립트를 생성할까요? (y/n, 기본값: y): " create_sample
    CREATE_SAMPLE="${create_sample:-y}"
  else
    CREATE_SAMPLE="y"
  fi
  
  if [[ "$CREATE_SAMPLE" =~ ^[Yy]$ ]]; then
    # 기본 샘플 스크립트
    cat > web_automation.py << 'EOF'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
설정 파일 기반의 Selenium 웹 자동화 스크립트
사용자가 config.json 파일을 통해 유동적으로 설정 가능
"""

import os
import sys
import time
import json
import logging
import argparse
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# 기본 설정값
DEFAULT_CONFIG = {
    "browser": {
        "type": "chrome",
        "headless": True,
        "options": [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--window-size=1920,1080"
        ]
    },
    "targets": [
        {
            "name": "기본 예제 사이트",
            "url": "https://www.example.com",
            "wait_for": {
                "type": "tag_name",
                "value": "body",
                "timeout": 10
            },
            "actions": [
                {
                    "type": "screenshot",
                    "filename": "example_site.png"
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

def setup_logging(config):
    """로깅 설정"""
    log_level = getattr(logging, config["output"].get("log_level", "INFO"))
    log_dir = config["output"].get("logs_dir", "logs")
    
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    log_file = os.path.join(log_dir, f"automation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("web_automation")

def load_config(config_path="config.json"):
    """설정 파일 로드"""
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config
        else:
            print(f"설정 파일을 찾을 수 없습니다: {config_path}")
            print("기본 설정 파일을 생성합니다.")
            
            # 기본 설정 파일 생성
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
            
            return DEFAULT_CONFIG
    except Exception as e:
        print(f"설정 파일 로드 실패: {e}")
        print("기본 설정을 사용합니다.")
        return DEFAULT_CONFIG

def setup_driver(config):
    """설정에 따라 웹 드라이버 설정"""
    browser_config = config["browser"]
    browser_type = browser_config.get("type", "chrome").lower()
    headless = browser_config.get("headless", True)
    browser_options = browser_config.get("options", [])
    
    # 브라우저 별 옵션 설정
    if browser_type == "chrome":
        options = ChromeOptions()
        if headless:
            options.add_argument("--headless")
        for option in browser_options:
            options.add_argument(option)
        # Service 객체와 경로 지정 없이 기본 설정 사용
        return webdriver.Chrome(options=options)
    
    elif browser_type == "firefox":
        options = FirefoxOptions()
        if headless:
            options.add_argument("--headless")
        for option in browser_options:
            options.add_argument(option)
        # Service 객체와 경로 지정 없이 기본 설정 사용
        return webdriver.Firefox(options=options)
    
    elif browser_type == "edge":
        options = EdgeOptions()
        if headless:
            options.add_argument("--headless")
        for option in browser_options:
            options.add_argument(option)
        # Service 객체와 경로 지정 없이 기본 설정 사용
        return webdriver.Edge(options=options)
    
    else:
        raise ValueError(f"지원되지 않는 브라우저 유형: {browser_type}")

def get_by_method(selector_type):
    """셀렉터 타입에 따른 By 메서드 반환"""
    selector_map = {
        'id': By.ID,
        'class_name': By.CLASS_NAME,
        'css': By.CSS_SELECTOR,
        'xpath': By.XPATH,
        'tag_name': By.TAG_NAME,
        'name': By.NAME,
        'link_text': By.LINK_TEXT,
        'partial_link_text': By.PARTIAL_LINK_TEXT
    }
    
    return selector_map.get(selector_type.lower(), By.CSS_SELECTOR)

def take_screenshot(driver, filename, config):
    """화면 캡처"""
    screenshots_dir = config["output"].get("screenshots_dir", "screenshots")
    
    if not os.path.exists(screenshots_dir):
        os.makedirs(screenshots_dir)
    
    if filename is None:
        filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    
    screenshot_path = os.path.join(screenshots_dir, filename)
    driver.save_screenshot(screenshot_path)
    return screenshot_path

def perform_action(driver, action, config, logger):
    """설정된 액션 수행"""
    action_type = action.get("type", "").lower()
    
    if action_type == "screenshot":
        filename = action.get("filename")
        screenshot_path = take_screenshot(driver, filename, config)
        logger.info(f"스크린샷 저장: {screenshot_path}")
    
    elif action_type == "input":
        selector = action.get("selector", {})
        selector_type = selector.get("type", "css")
        selector_value = selector.get("value", "")
        text = action.get("text", "")
        submit = action.get("submit", False)
        
        element = driver.find_element(get_by_method(selector_type), selector_value)
        element.clear()
        element.send_keys(text)
        
        if submit:
            element.send_keys(Keys.RETURN)
        
        logger.info(f"입력 완료: '{text}' (제출: {submit})")
    
    elif action_type == "click":
        selector = action.get("selector", {})
        selector_type = selector.get("type", "css")
        selector_value = selector.get("value", "")
        
        element = driver.find_element(get_by_method(selector_type), selector_value)
        element.click()
        
        logger.info(f"클릭 완료: {selector_value}")
    
    elif action_type == "wait":
        seconds = action.get("seconds", 1)
        time.sleep(seconds)
        logger.info(f"{seconds}초 대기 완료")
    
    elif action_type == "extract":
        selector = action.get("selector", {})
        selector_type = selector.get("type", "css")
        selector_value = selector.get("value", "")
        attribute = action.get("attribute", None)
        
        elements = driver.find_elements(get_by_method(selector_type), selector_value)
        results = []
        
        for element in elements:
            if attribute:
                results.append(element.get_attribute(attribute))
            else:
                results.append(element.text)
        
        logger.info(f"데이터 추출 완료: {len(results)}개 항목")
        
        # 결과 저장
        if action.get("save", False):
            results_dir = config["output"].get("results_dir", "results")
            if not os.path.exists(results_dir):
                os.makedirs(results_dir)
                
            output_file = action.get("output_file", f"extract_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
            output_path = os.path.join(results_dir, output_file)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                for idx, result in enumerate(results):
                    f.write(f"Item {idx+1}: {result}\n")
            
            logger.info(f"추출 결과 저장: {output_path}")
    
    elif action_type == "scroll":
        target = action.get("target", "bottom")
        amount = action.get("amount", None)
        
        if target == "bottom":
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        elif target == "top":
            driver.execute_script("window.scrollTo(0, 0);")
        elif amount:
            driver.execute_script(f"window.scrollBy(0, {amount});")
        
        logger.info(f"스크롤 완료: {target}")

def process_target(driver, target, config, logger):
    """대상 사이트 처리"""
    name = target.get("name", "Unnamed Target")
    url = target.get("url")
    
    logger.info(f"대상 처리 시작: {name} ({url})")
    
    # URL 접근
    driver.get(url)
    
    # 페이지 로딩 대기
    wait_config = target.get("wait_for", {})
    if wait_config:
        selector_type = wait_config.get("type", "tag_name")
        selector_value = wait_config.get("value", "body")
        timeout = wait_config.get("timeout", config["timeouts"].get("default_wait", 10))
        
        try:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((get_by_method(selector_type), selector_value))
            )
            logger.info(f"페이지 로딩 완료: {url}")
        except TimeoutException:
            logger.error(f"페이지 로딩 타임아웃: {url}")
            return False
    
    # 작업 수행
    actions = target.get("actions", [])
    for action in actions:
        try:
            perform_action(driver, action, config, logger)
        except Exception as e:
            logger.error(f"작업 수행 실패: {action.get('type')} - {e}")
    
    # 결과 저장
    results_dir = config["output"].get("results_dir", "results")
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
        
    result_file = os.path.join(
        results_dir, 
        f"result_{name.replace(' ', '_').replace('/', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    )
    
    with open(result_file, "w", encoding='utf-8') as f:
        f.write(f"대상: {name}\n")
        f.write(f"URL: {url}\n")
        f.write(f"제목: {driver.title}\n")
        f.write(f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    logger.info(f"결과 저장 완료: {result_file}")
    return True

def main():
    """메인 실행 함수"""
    # 명령줄 인자 처리
    parser = argparse.ArgumentParser(description='설정 파일 기반 웹 자동화 도구')
    parser.add_argument('-c', '--config', default='config.json', help='설정 파일 경로')
    parser.add_argument('-t', '--target', help='특정 대상만 실행 (이름)')
    parser.add_argument('--headless', action='store_true', help='헤드리스 모드 강제 적용')
    args = parser.parse_args()
    
    # 설정 파일 로드
    config = load_config(args.config)
    
    # 명령줄 인자로 설정 덮어쓰기
    if args.headless:
        config["browser"]["headless"] = True
    
    # 로깅 설정
    logger = setup_logging(config)
    logger.info(f"설정 파일 로드 완료: {args.config}")
    
    try:
        # 환경변수 확인 - 헤드리스 리눅스 환경에서 필요
        if "DISPLAY" not in os.environ and os.name == "posix" and config["browser"].get("headless", False):
            os.environ["DISPLAY"] = ":99"
            logger.info("DISPLAY 환경변수 설정: :99")
        
        # 드라이버 설정
        driver = setup_driver(config)
        logger.info(f"드라이버 설정 완료 (브라우저: {config['browser'].get('type')}, 헤드리스: {config['browser'].get('headless')})")
        
        try:
            # 대상 처리
            targets = config.get("targets", [])
            
            # 특정 대상만 처리 (명령줄 인자로 지정된 경우)
            if args.target:
                targets = [t for t in targets if t.get("name") == args.target]
                if not targets:
                    logger.error(f"지정된 대상을 찾을 수 없음: {args.target}")
                    sys.exit(1)
            
            for target in targets:
                process_target(driver, target, config, logger)
            
            logger.info("모든 작업 완료")
            
        except Exception as e:
            logger.error(f"예상치 못한 오류: {e}", exc_info=True)
        finally:
            # 브라우저 종료
            driver.quit()
            logger.info("드라이버 종료")
            
    except Exception as e:
        logger.error(f"자동화 실패: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
EOF

    # 헤드리스 모드 테스트 스크립트
    cat > test_headless.py << 'EOF'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
헤드리스 모드 테스트 스크립트
"""

import os
import sys
import logging
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.common.exceptions import WebDriverException

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("headless_test")

def main():
    """
    헤드리스 모드 테스트 실행
    """
    # 리눅스 환경에서 DISPLAY 환경변수 설정
    if "DISPLAY" not in os.environ and os.name == "posix":
        os.environ["DISPLAY"] = ":99"
        logger.info("DISPLAY 환경변수 설정: :99")
    
    # 현재 환경 정보 출력
    logger.info(f"운영체제: {os.name} ({sys.platform})")
    logger.info(f"파이썬 버전: {sys.version}")
    
    try:
        # 크롬 드라이버 경로
        # driver_path = os.path.join("drivers", "chromedriver")
        # if sys.platform.startswith("win"):
        #     driver_path += ".exe"
        
        # # 크롬 옵션 설정
        # options = ChromeOptions()
        # options.add_argument("--headless")
        # options.add_argument("--no-sandbox")
        # options.add_argument("--disable-dev-shm-usage")
        # options.add_argument("--window-size=1920,1080")
        
        # # 디버그 정보 출력
        # logger.info(f"드라이버 경로: {driver_path}")
        # logger.info(f"드라이버 옵션: {options.arguments}")
        
        # # 웹드라이버 시작
        # service = ChromeService(executable_path=driver_path)
        # driver = webdriver.Chrome(service=service, options=options)

        # v4.6 or newer use below
        driver = webdriver.Chrome(options=options)
        # 테스트 페이지 접속
        logger.info("웹 페이지 접속 시도...")
        driver.get("https://www.example.com")
        
        # 결과 출력
        logger.info(f"페이지 타이틀: {driver.title}")
        logger.info(f"페이지 URL: {driver.current_url}")
        
        # 스크린샷 저장
        screenshot_path = f"screenshots/headless_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        driver.save_screenshot(screenshot_path)
        logger.info(f"스크린샷 저장: {screenshot_path}")
        
        # 브라우저 종료
        driver.quit()
        logger.info("헤드리스 모드 테스트 성공")
        return True
    
    except WebDriverException as e:
        logger.error(f"웹드라이버 오류: {e}")
    except Exception as e:
        logger.error(f"예상치 못한 오류: {e}")
    
    logger.error("헤드리스 모드 테스트 실패")
    return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
EOF

    chmod +x web_automation.py
    chmod +x test_headless.py
    log_success "샘플 스크립트 생성 완료"
  else
    log_info "샘플 스크립트 생성을 건너뜁니다."
  fi
}

install_gemini_dependencies() {
  log_info "Gemini API 의존성 설치 중..."
  
  if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Python 가상 환경 활성화
    source venv/bin/activate
    
    # 필수 패키지 설치
    pip install google-generativeai python-dotenv requests
    
    log_success "Gemini API 의존성 설치 완료"
  else
    log_info "현재 운영체제에서는 추가 의존성이 필요하지 않습니다."
  fi
}

generate_gemini_config() {
  local task_description=$1
  local config_file=$2
  
  log_info "Gemini API를 이용한 config 생성 시작..."
  
  # Python 스크립트 실행
  python3 ../gemini/gemini_config_gen.py \
    --task "$task_description" \
    --output "$config_file"
  
  if [ -f "$config_file" ]; then
    log_success "Config 파일 생성 완료: $config_file"
  else
    log_error "Config 파일 생성 실패"
  fi
}


# 설치 후 안내사항 출력
print_post_setup_guide() {
  echo
  echo "===== 설치 후 안내사항 ====="
  echo
  echo "1. 가상환경 활성화 방법:"
  if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    echo "   venv\\Scripts\\activate"
  else
    echo "   source venv/bin/activate"
  fi
  echo
  echo "2. 헤드리스 모드 테스트:"
  echo "   python test_headless.py"
  echo
  echo "3. 샘플 스크립트 실행:"
  echo "   python web_automation.py"
  echo
  echo "4. 로그 및 스크린샷 확인:"
  echo "   - 로그: logs 디렉토리"
  echo "   - 스크린샷: screenshots 디렉토리"
  echo "   - 결과: results 디렉토리"
  echo
  echo "5. 문제 해결:"
  echo "   - 헤드리스 모드에서 문제가 발생하면 'export DISPLAY=:99' 명령 실행"
  echo "   - 드라이버 실행 권한 문제 발생 시 'chmod +x drivers/*' 명령 실행"
  echo
}

install_gemini_integration() {
  log_info "Gemini API 통합 설정 중..."
  
  # Gemini 디렉토리 생성
  mkdir -p ../gemini
  
  # Gemini 설정 파일 생성
cat > ../gemini/gemini_config_gen.py << 'EOFPY'
#!/usr/bin/env python3
import os
import json
import argparse
import re
import google.generativeai as genai
from dotenv import load_dotenv

class GeminiConfigGenerator:
    def __init__(self, api_key=None, max_retries=3):
        load_dotenv()
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.max_retries = max_retries
        self.task_description = ""
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")
            
        genai.configure(api_key=self.api_key)
        
        # 지원되는 모델로 변경
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # 설정 파일 템플릿
        self.config_template = {
            "browser": {
                "type": "chrome",
                "headless": True,
                "options": [
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--window-size=1920,1080",
                    "--incognito"
                ]
            },
            "targets": [],
            "output": {
                "log_level": "INFO",
                "results_dir": "results",
                "screenshots_dir": "screenshots",
                "logs_dir": "logs"
            },
            "timeouts": {
                "default_wait": 30,
                "page_load": 60
            }
        }
        
        # 유효한 셀렉터 타입 목록
        self.valid_selector_types = [
            "id", "css", "xpath", "class_name", "tag_name", "name", "link_text", "partial_link_text"
        ]
        
        # 유효한 액션 타입 목록
        self.valid_action_types = [
            "screenshot", "input", "click", "wait", "extract", "scroll"
        ]

    def generate_config(self, task_description):
        """유효한 설정 파일을 생성할 때까지 반복 시도"""
        self.task_description = task_description

        for attempt in range(self.max_retries):
            print(f"설정 파일 생성 시도 중... (시도 {attempt+1}/{self.max_retries})")
            
            # 설정 파일 생성 시도
            config = self._generate_config_attempt(task_description)
            
            # 유효성 검사
            validation_result, issues = self.validate_config(config)
            
            if validation_result:
                print("유효한 설정 파일이 생성되었습니다.")
                return config
            else:
                print(f"설정 파일 유효성 검사 실패: {', '.join(issues)}")
                
                # 다음 시도에는 이전 문제점을 포함하여 더 나은 결과 요청
                if attempt < self.max_retries - 1:
                    task_description = self._add_validation_feedback(task_description, issues)
        
        # 모든 시도가 실패하면 안전한 기본 설정 사용
        print("최대 시도 횟수를 초과했습니다. 안전한 기본 설정을 사용합니다.")
        return self._create_default_config(task_description)

    def _generate_config_attempt(self, task_description):
        """Gemini API를 통한 설정 파일 생성 시도"""
        prompt = f"""
        다음 작업 설명을 바탕으로 Selenium 자동화 설정 파일을 JSON 형식으로 생성해주세요.
        반드시 다음 구조를 준수해야 합니다:
        
        {json.dumps(self.config_template, indent=2, ensure_ascii=False)}
        
        작업 설명: {task_description}
        
        중요한 주의사항:
        1. targets 배열에는 최소 1개 이상의 작업 단계를 포함해야 합니다
        2. 각 액션은 유효한 Selenium 명령어를 사용해야 합니다
        3. 모든 selectors는 반드시 유효한 값을 포함해야 합니다:
           - selector 객체에는 항상 "type"과 "value" 속성이 있어야 합니다
           - selector의 "value"는 절대 비어있으면 안됩니다
           - 각 selector의 "type"은 다음 중 하나여야 합니다: {', '.join(self.valid_selector_types)}
        4. 네이버 검색 버튼 CSS 선택자:
           - 검색창: "#query" 또는 "input[name='query']"
           - 검색 버튼: ".btn_search" 또는 "button.btn_search"
        5. 각 액션 타입은 다음 중 하나여야 합니다: {', '.join(self.valid_action_types)}
        6. 반드시 유효한 JSON 형식이어야 합니다
        
        모든 셀렉터에는 명확하고 구체적인 값이 포함되어야 합니다. "click" 액션의 경우, 항상 유효한 selector 객체를 지정해야 합니다.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return self._extract_and_validate_config(response.text)
        except Exception as e:
            print(f"Gemini API 호출 중 오류 발생: {e}")
            return self._create_default_config(task_description)

    def _extract_and_validate_config(self, raw_text):
        """텍스트에서 JSON 부분 추출 및 기본 검증"""
        try:
            # 텍스트에서 JSON 부분 추출 시도
            json_start = raw_text.find('{')
            json_end = raw_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = raw_text[json_start:json_end]
                config = json.loads(json_str)
                
                # 필수 필드 검증
                required_fields = ['browser', 'targets', 'output', 'timeouts']
                for field in required_fields:
                    if field not in config:
                        raise ValueError(f"필수 필드 누락: {field}")
                
                return config
            else:
                raise ValueError("JSON 형식을 찾을 수 없습니다")
        except Exception as e:
            print(f"JSON 파싱 오류: {e}")
            print("기본 템플릿을 사용합니다")
            return self._create_default_config(self.task_description)

    def _create_default_config(self, task_description):
        """안전한 기본 설정 파일 생성"""
        default_config = self.config_template.copy()
        
        # 작업 설명에 따라 맞춤형 기본 설정 구성
        if "네이버" in task_description.lower() and "검색" in task_description.lower():
            # 검색어 추출
            search_term = "chicken"  # 기본값
            if "검색" in task_description:
                # 작업 설명에서 따옴표로 둘러싸인 검색어 추출 시도
                search_match = re.search(r"['\"](.*?)['\"]", task_description)
                if search_match:
                    search_term = search_match.group(1)
            
            default_config["targets"] = [{
                "name": f"네이버 {search_term} 검색 결과 추출",
                "url": "https://www.naver.com",
                "wait_for": {
                    "type": "id",
                    "value": "query",
                    "timeout": 10
                },
                "actions": [
                    {
                        "type": "input",
                        "selector": {
                            "type": "id",
                            "value": "query"
                        },
                        "text": search_term,
                        "submit": False
                    },
                    {
                        "type": "click",
                        "selector": {
                            "type": "css",
                            "value": ".btn_search"
                        }
                    },
                    {
                        "type": "wait",
                        "seconds": 3
                    },
                    {
                        "type": "screenshot",
                        "filename": "naver_search_results.png"
                    },
                    {
                        "type": "extract",
                        "selector": {
                            "type": "css",
                            "value": ".total_tit"
                        },
                        "save": True,
                        "output_file": f"{search_term}_search_results.txt"
                    }
                ]
            }]
        else:
            # 일반적인 기본 설정
            default_config["targets"] = [{
                "name": "기본 예제 사이트",
                "url": "https://www.example.com",
                "wait_for": {
                    "type": "tag_name",
                    "value": "body",
                    "timeout": 10
                },
                "actions": [
                    {
                        "type": "screenshot",
                        "filename": "example_site.png"
                    }
                ]
            }]
            
        return default_config

    def validate_config(self, config):
        """설정 파일의 모든 셀렉터와 액션 유효성 검사"""
        issues = []
        
        # 대상 검증
        if not config.get("targets") or len(config["targets"]) == 0:
            issues.append("최소 하나 이상의 대상이 필요합니다")
            return False, issues
            
        # 각 대상 검증
        for target_idx, target in enumerate(config["targets"]):
            # 필수 필드 검증
            if "name" not in target:
                issues.append(f"대상 #{target_idx+1}에 이름이 없습니다")
            
            if "url" not in target:
                issues.append(f"대상 #{target_idx+1}에 URL이 없습니다")
            
            if "actions" not in target or not target["actions"]:
                issues.append(f"대상 #{target_idx+1}에 액션이 없습니다")
                continue
                
            # 각 액션 검증
            for action_idx, action in enumerate(target["actions"]):
                if "type" not in action:
                    issues.append(f"대상 #{target_idx+1}, 액션 #{action_idx+1}에 타입이 없습니다")
                    continue
                    
                action_type = action["type"].lower()
                
                # 액션 타입 검증
                if action_type not in self.valid_action_types:
                    issues.append(f"대상 #{target_idx+1}, 액션 #{action_idx+1}의 타입이 잘못되었습니다: {action_type}")
                
                # 셀렉터가 필요한 액션인 경우 셀렉터 검증
                if action_type in ["input", "click", "extract"]:
                    selector_issues = self._validate_selector(action, target_idx, action_idx)
                    issues.extend(selector_issues)
        
        return len(issues) == 0, issues

    def _validate_selector(self, action, target_idx, action_idx):
        """액션의 셀렉터 유효성 검사"""
        issues = []
        
        # 셀렉터 존재 여부 확인
        if "selector" not in action:
            issues.append(f"대상 #{target_idx+1}, 액션 #{action_idx+1}에 셀렉터가 없습니다")
            return issues
            
        selector = action["selector"]
        
        # 셀렉터 타입 확인
        if "type" not in selector:
            issues.append(f"대상 #{target_idx+1}, 액션 #{action_idx+1}의 셀렉터에 타입이 없습니다")
        elif selector["type"] not in self.valid_selector_types:
            issues.append(f"대상 #{target_idx+1}, 액션 #{action_idx+1}의 셀렉터 타입이 잘못되었습니다: {selector['type']}")
            
        # 셀렉터 값 확인
        if "value" not in selector:
            issues.append(f"대상 #{target_idx+1}, 액션 #{action_idx+1}의 셀렉터에 값이 없습니다")
        elif not selector["value"] or len(selector["value"].strip()) == 0:
            issues.append(f"대상 #{target_idx+1}, 액션 #{action_idx+1}의 셀렉터 값이 비어 있습니다")
            
        # 셀렉터 문법 검증
        if "type" in selector and "value" in selector:
            selector_type = selector["type"]
            selector_value = selector["value"]
            
            if selector_type == "css":
                # CSS 선택자 형식 검증
                if self._has_invalid_css_syntax(selector_value):
                    issues.append(f"대상 #{target_idx+1}, 액션 #{action_idx+1}의 CSS 선택자 구문이 잘못되었습니다: {selector_value}")
            
            elif selector_type == "xpath":
                # XPath 형식 검증
                if self._has_invalid_xpath_syntax(selector_value):
                    issues.append(f"대상 #{target_idx+1}, 액션 #{action_idx+1}의 XPath 선택자 구문이 잘못되었습니다: {selector_value}")
                    
        return issues

    def _has_invalid_css_syntax(self, css_selector):
        """CSS 선택자 구문 기본 검증"""
        # 비어있는 선택자
        if not css_selector or len(css_selector.strip()) == 0:
            return True
            
        # 괄호 짝이 맞지 않는 경우
        if css_selector.count('(') != css_selector.count(')'):
            return True
            
        if css_selector.count('[') != css_selector.count(']'):
            return True
            
        # 콜론 뒤에 값이 없는 경우
        if re.search(r':[a-zA-Z-]+\(\s*\)', css_selector):
            return True
            
        return False

    def _has_invalid_xpath_syntax(self, xpath_selector):
        """XPath 선택자 구문 기본 검증"""
        # 비어있는 선택자
        if not xpath_selector or len(xpath_selector.strip()) == 0:
            return True
            
        # 괄호 짝이 맞지 않는 경우
        if xpath_selector.count('(') != xpath_selector.count(')'):
            return True
            
        if xpath_selector.count('[') != xpath_selector.count(']'):
            return True
            
        # 따옴표 짝이 맞지 않는 경우
        if xpath_selector.count("'") % 2 != 0:
            return True
            
        if xpath_selector.count('"') % 2 != 0:
            return True
            
        return False

    def _add_validation_feedback(self, task_description, issues):
        """유효성 검사 결과를 피드백으로 추가하여 다음 시도 개선"""
        feedback = "\n\n이전 시도에서 다음과 같은 문제가 발생했습니다:\n"
        for issue in issues:
            feedback += f"- {issue}\n"
            
        feedback += "\n위 문제들을 수정하여 다시 설정 파일을 생성해주세요."
        
        return task_description + feedback

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gemini API를 이용한 Selenium 설정 파일 생성")
    parser.add_argument("--task", required=True, help="자동화 작업 설명")
    parser.add_argument("--output", default="gemini_generated_config.json", help="출력 파일 경로")
    parser.add_argument("--api-key", help="Gemini API 키")
    parser.add_argument("--max-retries", type=int, default=5, help="최대 시도 횟수")
    parser.add_argument("--validate-only", action="store_true", help="기존 설정 파일만 검증")
    
    args = parser.parse_args()
    
    generator = GeminiConfigGenerator(api_key=args.api_key, max_retries=args.max_retries)
    
    if args.validate_only and os.path.exists(args.output):
        # 기존 설정 파일 검증
        with open(args.output, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        is_valid, issues = generator.validate_config(config)
        if is_valid:
            print(f"설정 파일이 유효합니다: {args.output}")
        else:
            print(f"설정 파일에 다음과 같은 문제가 있습니다:")
            for issue in issues:
                print(f"- {issue}")
    else:
        # 새 설정 파일 생성
        config = generator.generate_config(args.task)
        
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print(f"생성된 설정 파일: {args.output}")
EOFPY

  # 실행 권한 부여
  chmod +x ../gemini/gemini_config_gen.py
  
  # 의존성 설치
  source ../setup/venv/bin/activate
  pip install google-generativeai python-dotenv
  pip install --upgrade google-generativeai python-dotenv
  
  # .env 파일 템플릿 생성
  if [ ! -f .env ]; then
    echo "# Gemini API 키 설정" > .env
    echo "GEMINI_API_KEY=your_api_key_here" >> .env
    log_info ".env 파일이 생성되었습니다. API 키를 설정해주세요."
  fi
  
  log_success "Gemini API 통합 설정 완료"
}


# 명령줄 인자
parse_arguments() {
  while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
      --gemini)
        INSTALL_GEMINI=true
        shift
        ;;
      --gemini-api-key)
        GEMINI_API_KEY="$2"
        shift 2
        ;;
      --gemini-task)
        GEMINI_TASK="$2"
        GEMINI_ENABLED=true
        shift 2
        ;;
      --gemini-output)
        GEMINI_CONFIG_OUTPUT="$2"
        shift 2
        ;;
      -n|--non-interactive)
        NON_INTERACTIVE=true
        shift
        ;;
      -b|--browser)
        BROWSER_TYPE="$2"
        shift 2
        ;;
      -p|--packages)
        PACKAGE_LEVEL="$2"
        shift 2
        ;;
      -h|--headless)
        HEADLESS_MODE=true
        shift
        ;;
      --help)
        show_help
        ;;
      *)
      echo "Unknown argument: $1"
      show help
      ;;
    esac
  done
}

# 메인 함수
main() {
  echo "===== Selenium 웹 자동화 환경 설정 ====="
  
  # 환경변수 및 기본값 설정
  export SELENIUM_SETUP_DIR=$(pwd)
  
  setup_logging
  parse_arguments "$@"
  load_config
  create_directories
  setup_environment
  
  if [ "$HEADLESS_MODE" = true ]; then
    install_headless_dependencies
  fi
  
  setup_virtualenv
  install_python_packages
  install_browser_drivers
  
  if [ "$INSTALL_GEMINI" = true ]; then
    install_gemini_integration
    
    # GEMINI_TASK가 설정된 경우에만 config 생성
    if [ ! -z "$GEMINI_TASK" ] && [ ! -z "$GEMINI_CONFIG_OUTPUT" ]; then
      generate_gemini_config "$GEMINI_TASK" "$GEMINI_CONFIG_OUTPUT"
    fi
  fi
    
  generate_sample_script
  
  log_success "셀레니움 웹 자동화 환경 설정이 완료되었습니다."
  
  print_post_setup_guide
}
# 스크립트 시작
main "$@"
