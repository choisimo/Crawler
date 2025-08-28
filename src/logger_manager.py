class LoggerManager:

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

    def _log_prompt_error(self, prompt):
        """프롬프트 오류 기록"""
        error_dir = os.path.join(self.temp_dir, 'prompt_errors')
        os.makedirs(error_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        error_file = os.path.join(error_dir, f'error_prompt_{timestamp}.txt')

        with open(error_file, 'w', encoding='utf-8') as f:
            f.write("=== 오류 발생 프롬프트 ===")
            f.write(prompt)

    def _setup_logging(self):
        """로깅 시스템 초기화"""
        # 로거 생성
        self.logger = logging.getLogger('GeminiConfigGenerator')
        self.logger.setLevel(logging.INFO)

        # 콘솔 핸들러 추가
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # 파일 핸들러 (선택적)
        if hasattr(self, 'temp_dir') and self.temp_dir:
            log_dir = os.path.join(self.temp_dir, 'logs')
            os.makedirs(log_dir, exist_ok=True)
            file_handler = logging.FileHandler(
                os.path.join(log_dir, f'gemini_config_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
