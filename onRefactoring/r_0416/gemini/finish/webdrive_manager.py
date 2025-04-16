
class WebDriveManager:

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
                        logger.warning(f"시도 {attempt + 1}/{max_retries}: Chrome 프로세스 정리 시도")
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