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
import uuid
import tempfile
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

def setup_driver(config, logger=None):
    import tempfile
    import psutil
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.firefox.options import Options as FirefoxOptions
    from selenium.webdriver.edge.options import Options as EdgeOptions

    browser_config = config["browser"]
    browser_type = browser_config.get("type", "chrome").lower()
    headless = browser_config.get("headless", True)
    browser_options = browser_config.get("options", [])

    if browser_type == "chrome":
        # user_data_dir 생성
        user_data_dir = tempfile.mkdtemp(prefix=f'chrome_{uuid.uuid4().hex}_')
        logger.info(f"생성된 user-data-dir: {user_data_dir}")

        options = ChromeOptions()
        options.add_argument(f"--user-data-dir={user_data_dir}")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        if headless:
            options.add_argument("--headless=new")
        for opt in browser_options:
            if not opt.startswith("--user-data-dir="):
                options.add_argument(opt)

        max_retries = int(config["browser"].get("retries", 5))
        for attempt in range(max_retries):
            try:
                driver = webdriver.Chrome(options=options)
                driver.user_data_dir = user_data_dir
                return driver
            except WebDriverException as e:
                if "user data directory is already in use" in str(e) and attempt < max_retries - 1:
                    logger.warning(f"시도 {attempt+1}/{max_retries}: Chrome 프로세스 정리 시도")
                    _cleanup_chrome_processes(user_data_dir, logger)
                    time.sleep(2)
                    continue
                raise

    elif browser_type == "firefox":
        options = FirefoxOptions()
        if headless:
            options.add_argument("--headless")
        for option in browser_options:
            options.add_argument(option)
        return webdriver.Firefox(options=options)

    elif browser_type == "edge":
        options = EdgeOptions()
        if headless:
            options.add_argument("--headless")
        for option in browser_options:
            options.add_argument(option)
        return webdriver.Edge(options=options)

    else:
        raise ValueError(f"지원되지 않는 브라우저 유형: {browser_type}")

def _cleanup_chrome_processes(user_data_dir, logger):
    """특정 user-data-dir을 사용하는 Chrome 프로세스 종료"""
    import psutil
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'chrome' in proc.info['name'].lower() and \
               any(f'--user-data-dir={user_data_dir}' in cmd for cmd in proc.info['cmdline']):
                logger.info(f"종료 대상 프로세스: PID={proc.pid}, CMD={' '.join(proc.info['cmdline'])}")
                proc.terminate()
                try:
                    proc.wait(3)
                except psutil.TimeoutExpired:
                    logger.warning(f"강제 종료: PID={proc.pid}")
                    proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

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
    parser = argparse.ArgumentParser(description='설정 파일 기반 웹 자동화 도구')
    parser.add_argument('-c', '--config', default='config.json', help='설정 파일 경로')
    parser.add_argument('-t', '--target', help='특정 대상만 실행 (이름)')
    parser.add_argument('--headless', action='store_true', help='헤드리스 모드 강제 적용')
    parser.add_argument('--retries', type=int, default=3, help='Chrome 프로세스 종료 재시도 횟수')
    args = parser.parse_args()
    
    # 설정 파일 로드
    config = load_config(args.config)
    
    # 명령줄 인자로 설정 덮어쓰기
    if args.headless:
        config["browser"]["headless"] = True
    if args.retries:
        config["browser"]["retries"] = args.retries
    # 로깅 설정
    logger = setup_logging(config)
    logger.info(f"설정 파일 로드 완료: {args.config}")
    
    try:
        # 환경변수 확인 - 헤드리스 리눅스 환경에서 필요
        if "DISPLAY" not in os.environ and os.name == "posix" and config["browser"].get("headless", False):
            os.environ["DISPLAY"] = ":99"
            logger.info("DISPLAY 환경변수 설정: :99")
        
        # 드라이버 설정 - logger 인자 전달
        driver = None
        user_data_dir = None
        try:
            driver = setup_driver(config, logger)
            logger.info(f"드라이버 설정 완료 (브라우저: {config['browser'].get('type')}, 헤드리스: {config['browser'].get('headless')})")
        except Exception as e:
            logger.error(f"자동화 실패: {e}", exc_info=True)
            sys.exit(1)
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
        try:
            if driver:
                driver.quit()
                logger.info("드라이버 종료 완료")
        except Exception as e:
            logger.error(f"드라이버 종료 실패: {e}")

        # user_data_dir 정리 (Chrome 전용)
        try:
            if driver and hasattr(driver, "user_data_dir"):
                import shutil
                user_data_dir = driver.user_data_dir
                if os.path.exists(user_data_dir):
                    shutil.rmtree(user_data_dir, ignore_errors=True)
                    logger.info(f"임시 디렉터리 삭제: {user_data_dir}")
        except Exception as e:
            logger.error(f"임시 디렉터리 삭제 실패: {e}")

if __name__ == "__main__":
    main()
