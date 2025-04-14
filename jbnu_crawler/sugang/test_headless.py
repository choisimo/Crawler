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
