class GeminiApi:
    load_dotenv()
    self.api_key = api_key or os.getenv("GEMINI_API_KEY")
    self.max_retries = max_retries
    self.task_description = ""
    self.verbose = verbose
    self.temp_dir = temp_dir or os.getcwd()
    self.safe_formatter = EnhancedSafeFormatter()
    self.user_url = None
    # 로깅 설정
    self._setup_logging()

    # 기본 프롬프트 템플릿 설정
    self.default_prompt_template = """
        다음 작업 설명을 바탕으로 Selenium 웹 자동화 설정 파일을 JSON 형식으로 생성해주세요.

        작업 설명: {task_description}

        생성할 설정 파일은 다음 조건을 반드시 충족해야 합니다:
        1. 다양한 웹사이트에 사용할 수 있는 범용적인 구조를 가져야 합니다.
        2. 사이트 방문, 정보 검색, 데이터 추출, 스크린샷 촬영 등의 기본적인 기능을 포함해야 합니다.
        3. 검색 기능을 사용할 경우 적절한 입력 필드와 검색 버튼을 찾을 수 있어야 합니다.
        4. 결과 데이터를 정확히 추출할 수 있도록 구체적인 셀렉터가 정의되어야 합니다.
        5. 페이지 로딩 시간을 고려한 적절한 대기 시간이 설정되어야 합니다.

        응답은 반드시: 
        - 유효한 JSON 형식이어야 합니다 (주석 없음)
        - 모든 속성명은 따옴표로 감싸야 합니다
        - 특수 문자나 제어 문자는 이스케이프 처리해야 합니다
        """

    if not self.api_key:
        raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")

    genai.configure(api_key=self.api_key)

    # 지원되는 모델로 변경
    self.model = genai.GenerativeModel('gemini-1.5-flash')

    self.config_template = {
        "targetUrl": "https://example.com",
        "browser": {
            "type": "chrome",
            "headless": True
        },
        "timeouts": {"implicit": 10},
        "output": {"format": "json"},
        "targets": [
            {
                "name": "기본 작업",
                "url": "https://example.com",
                "actions": []
            }
        ],
        "selectors": {},
        "actions": []
    }

    # 유효한 셀렉터 타입 목록
    self.valid_selector_types = [
        "id", "css", "xpath", "class_name", "tag_name", "name", "link_text", "partial_link_text"
    ]

    # 유효한 액션 타입 목록
    self.valid_action_types = [
        "screenshot", "input", "click", "wait", "extract", "scroll"
    ]


    def generate_config(self, task_description, custom_prompt=None, user_url=None):
        """유효한 설정 파일을 생성할 때까지 반복 시도"""

        self.user_url = self._fix_url(user_url) if user_url else None

        if self.user_url:
            self.config_template["targetUrl"] = self.user_url
            if self.config_template.get("targets"):
                self.config_template["targets"][0]["url"] = self.user_url

        self.task_description = task_description

        for attempt in range(self.max_retries):
            print(f"설정 파일 생성 시도 중... (시도 {attempt + 1}/{self.max_retries})")

            # 설정 파일 생성 시도
            config = self._generate_config_attempt(task_description, custom_prompt)

            if self.user_url:
                config["targetUrl"] = self.user_url  # 변경된 부분
                if hasattr(self, 'logger'):
                    self.logger.info(f"URL 강제 적용: {self.user_url}")

            # 반환값이 튜플인 경우 처리 (기본 설정 + 플래그 형태로 반환될 수 있음)
            if isinstance(config, tuple):
                config = config[0]  # 첫 번째 요소가 설정 객체

            # targetUrl 필드 자동 추가 - 오류 발생 대신 필드 추가
            if "targetUrl" not in config:
                if self.user_url:
                    config["targetUrl"] = self.user_url
                    if hasattr(self, 'logger'):
                        self.logger.info(f"targetUrl 필드 자동 추가: {self.user_url}")
                else:
                    # 작업 설명에서 URL 추출 시도
                    url_match = re.search(r'https?://[^\s"\'<>]+', task_description)
                    if url_match:
                        config["targetUrl"] = url_match.group(0)
                        if hasattr(self, 'logger'):
                            self.logger.info(f"작업 설명에서 URL 추출하여 추가: {config['targetUrl']}")
                    elif "reddit" in task_description.lower():
                        config["targetUrl"] = "https://www.reddit.com"
                        if hasattr(self, 'logger'):
                            self.logger.info("Reddit URL 자동 추가")
                    else:
                        # 기본값으로 설정
                        config["targetUrl"] = "https://example.com"
                        if hasattr(self, 'logger'):
                            self.logger.info("기본 URL 설정")

            # URL 유효성 검사 (계속 진행)
            if config["targetUrl"] == 'https://example.com':
                print("⚠️ 경고: 기본 URL이 사용되었습니다. 명시적인 URL 지정을 권장합니다.")
            elif config["targetUrl"] == 'https://':
                print("⚠️ 경고: 불완전한 URL이 설정되었습니다. URL을 다시 확인하세요.")
                config["targetUrl"] = "https://www.example.com"

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
        default_config = self._create_default_config(task_description)

        # 기본 설정에도 URL 적용
        if self.user_url and "targetUrl" not in default_config:
            default_config["targetUrl"] = self.user_url

        return default_config


    def _generate_config_attempt(self, task_description, custom_prompt=None):
        """Gemini API를 통한 설정 파일 생성 시도"""
        try:
            if not custom_prompt:
                # 기본 프롬프트 사용 (기존 코드와 동일하게 유지)
                prompt_template = self.default_prompt_template
                prompt = prompt_template.format(task_description=task_description)
                # 추가 정보 포함
                url_context = ""
                if self.user_url:
                    url_context = f"\n대상 사이트 URL: {self.user_url}\n"

                prompt += f"""
    
    
                    설정 파일 구조는 다음과 같아야 합니다:
                    {json.dumps(self.config_template, indent=2, ensure_ascii=False)}
    
                    중요한 주의사항:
                    1. targets 배열에는 최소 1개 이상의 작업 단계를 포함해야 합니다
                    2. 각 액션은 유효한 Selenium 명령어를 사용해야 합니다
                    3. 모든 selectors는 반드시 유효한 값을 포함해야 합니다:
                        - selector 객체에는 항상 "type"과 "value" 속성이 있어야 합니다
                        - selector의 "value"는 절대 비어있으면 안됩니다
                        - 각 selector의 "type"은 다음 중 하나여야 합니다: {', '.join(self.valid_selector_types)}
                    4. 각 액션 타입은 다음 중 하나여야 합니다: {', '.join(self.valid_action_types)}
                    5. 웹사이트 특성에 맞게 적절한 셀렉터와 대기 시간을 설정해야 합니다
                    """
            else:
                # 사용자 정의 프롬프트 처리
                try:
                    # 1. 미리 전처리된 프롬프트 사용
                    # URL과 JSON 블록이 전처리되어 있어야 함

                    # 2. 포맷 변수 준비
                    format_vars = {
                        "task_description": task_description,
                        "config_template": json.dumps(self.config_template, indent=2, ensure_ascii=False),
                        "valid_selector_types": ", ".join(self.valid_selector_types),
                        "valid_action_types": ", ".join(self.valid_action_types),
                        "current_date": datetime.now().strftime('%Y-%m-%d')
                    }

                    # 3. 향상된 안전 포맷터 사용
                    formatter = EnhancedSafeFormatter()
                    prompt = formatter.format(custom_prompt, **format_vars)

                except Exception as e:
                    # 내부 try-except 블록: 프롬프트 포맷팅 오류 처리
                    error_message = f"프롬프트 포맷팅 실패: {e}"
                    print(error_message)
                    if hasattr(self, 'logger'):
                        self.logger.error(error_message, exc_info=True)

                    # 실패한 프롬프트 저장 (문제 진단용)
                    self._save_failed_prompt(custom_prompt, format_vars)

                    # 포맷팅 문제를 우회하는 대체 방법 시도
                    prompt = self._create_fallback_prompt(task_description, custom_prompt)
                    if not prompt:
                        return self._create_default_config(task_description), True

            # API 호출 부분
            if hasattr(self, 'logger'):
                self.logger.info("Gemini API 호출 준비 완료")

            try:
                # API 호출
                response = self.model.generate_content(prompt)
                raw_text = response.text

                # JSON 추출 및 검증
                config = self._extract_and_validate_config(raw_text)
                return config

            except Exception as e:
                # API 호출 오류 처리
                print(f"Gemini API 호출 중 오류 발생: {e}")
                if hasattr(self, 'logger'):
                    self.logger.error(f"API 오류: {e}", exc_info=True)
                return self._create_default_config(task_description), True

        except Exception as e:
            # 외부 try-except 블록: 전체 메서드 오류 처리
            print(f"설정 파일 생성 시도 중 오류 발생: {e}")
            if hasattr(self, 'logger'):
                self.logger.error(f"예상치 못한 오류: {e}", exc_info=True)
            return self._create_default_config(task_description), True


    def _save_failed_prompt(self, prompt, format_vars):
        """실패한 프롬프트 저장 (디버깅용)"""
        debug_dir = os.path.join(self.temp_dir, 'prompt_debug')
        os.makedirs(debug_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 원본 프롬프트 저장
        with open(os.path.join(debug_dir, f'failed_prompt_{timestamp}.txt'), 'w', encoding='utf-8') as f:
            f.write(prompt)

        # 포맷 변수 저장
        with open(os.path.join(debug_dir, f'format_vars_{timestamp}.json'), 'w', encoding='utf-8') as f:
            # 문자열 변환 가능한 값만 저장
            safe_vars = {}
            for k, v in format_vars.items():
                try:
                    safe_vars[k] = str(v)
                except:
                    safe_vars[k] = f"<{type(v).__name__}>"
            json.dump(safe_vars, f, indent=2, ensure_ascii=False)

        """텍스트에서 JSON 부분 추출 및 기본 검증"""
        try:
            # 텍스트에서 JSON 부분 추출 시도
            json_start = raw_text.find('{')
            json_end = raw_text.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_str = raw_text[json_start:json_end]

                # 임시 저장 디렉토리 생성
                if hasattr(self, 'temp_dir') and self.verbose:
                    debug_dir = os.path.join(self.temp_dir, 'json_debug')
                    os.makedirs(debug_dir, exist_ok=True)

                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    original_json_path = os.path.join(debug_dir, f'original_json_{timestamp}.json')

                    with open(original_json_path, 'w', encoding='utf-8') as f:
                        f.write(json_str)

                    if hasattr(self, 'logger'):
                        self.logger.debug(f"원본 JSON 저장: {original_json_path}")

                # 주석 제거 및 처리...
                json_str = re.sub(r'//.*?(\n|$)', '', json_str)
                json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
                json_str = re.sub(r',\s*}', '}', json_str)
                json_str = re.sub(r',\s*]', ']', json_str)

                # 추가: 제어 문자 제거
                json_str = re.sub(r'[\x00-\x1F\x7F]', '', json_str)

                # 추가: 따옴표 없는 키 처리
                json_str = re.sub(r'([{,]\s*)(\w+)(\s*:)', r'\1"\2"\3', json_str)

                try:
                    # JSON 파싱 시도...
                    config = json.loads(json_str)
                    if self.user_url and "targetUrl" not in config:
                        config["targetUrl"] = self.user_url

                    return config
                except Exception as e:
                    error_message = f"JSON 파싱 오류: {e}"
                    print(error_message)

                    # 실패한 JSON 저장
                    self._save_failed_json(json_str, error_message, "parsing")

                    # Gemini API를 사용하여 JSON 수정 시도
                    print("Gemini API를 사용하여 JSON 수정 시도 중...")
                    fixed_config = self._fix_json_with_gemini(json_str)

                    if fixed_config:
                        print("Gemini API로 JSON 수정 성공")
                        return fixed_config

                    print("기본 템플릿을 사용합니다")
                    return self._create_default_config(self.task_description)
        except Exception as e:
            print(f"처리 중 오류: {e}")
            default_config = self._create_default_config(self.task_description)

            # targets 배열 확인 및 생성
            if "targets" not in default_config or not default_config["targets"]:
                default_config["targets"] = [{
                    "name": "기본 작업",
                    "url": default_config["targetUrl"],
                    "actions": []
                }]

            return default_config

    def _fix_json_with_gemini(self, invalid_json):
        url_info = f'\n반드시 "targetUrl": "{self.user_url}" 필드를 포함해야 합니다.' if self.user_url else ''

        """Gemini API를 사용하여 잘못된 JSON 수정 시도"""
        prompt = f"""
        다음은 잘못된 형식의 JSON 문자열입니다. 이를 올바른 Selenium 자동화 설정 JSON으로 수정해주세요.

        {url_info}  

        잘못된 JSON:
        ```
        {invalid_json}
        ```

        수정된 JSON은 다음 필수 요구사항을 충족해야 합니다:
        1. 모든 문자열은 큰따옴표로 묶여야 합니다.
        2. 객체의 키 이름은 큰따옴표로 묶여야 합니다.
        3. 마지막 항목 뒤에 콤마가 없어야 합니다.
        4. "targets" 배열이 반드시 존재해야 하며, 최소 1개 이상의 작업 대상을 포함해야 합니다.
        5. 각 target 객체는 "name", "url", "actions" 필드를 포함해야 합니다.
        6. "actions" 배열에는 최소 1개 이상의 동작이 포함되어야 합니다.

        대상 사이트가 수강신청 시스템이므로, 다음 요소를 포함하는 것이 좋습니다:
        - 로그인 기능 (ID/PWD 입력)
        - 과목 검색 및 선택 기능
        - 수강신청 버튼 클릭 기능

        응답은 수정된 JSON만 포함해야 합니다. 다른 설명이나 텍스트는 포함하지 마세요.

        반드시 다음 구조를 포함해야 합니다:
        {{
        "targetUrl": "사용자_제공_URL",
        "targets": [
            {{
            "name": "작업_이름",
            "url": "대상_URL",
            "actions": []
            }}
        ]
        }}
        """

        try:
            if hasattr(self, 'logger'):
                self.logger.info("Gemini API를 사용하여 JSON 수정 시도 중...")

            response = self.model.generate_content(prompt)
            fixed_json_str = response.text

            if hasattr(self, 'logger'):
                self.logger.debug(f"Gemini API 응답: {fixed_json_str[:200]}...")

            # JSON 문자열에서 JSON 객체 부분만 추출
            # 코드 블록이 있는 경우 추출
            backtick = '`'
            code_block_marker = backtick * 3

            if code_block_marker in fixed_json_str:
                pattern = r'``````'
                match = re.search(pattern, fixed_json_str)
                if match:
                    fixed_json_str = match.group(1).strip()

            # JSON 시작과 끝 찾기
            json_start = fixed_json_str.find('{')
            json_end = fixed_json_str.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                fixed_json_str = fixed_json_str[json_start:json_end]

                # 수정된 JSON 저장 (디버깅용)
                if hasattr(self, 'temp_dir'):
                    debug_dir = os.path.join(self.temp_dir, 'json_debug')
                    os.makedirs(debug_dir, exist_ok=True)

                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    fixed_json_path = os.path.join(debug_dir, f'fixed_json_{timestamp}.json')

                    with open(fixed_json_path, 'w', encoding='utf-8') as f:
                        f.write(fixed_json_str)

                    if hasattr(self, 'logger'):
                        self.logger.debug(f"수정된 JSON 저장: {fixed_json_path}")

                # JSON 파싱 시도
            try:
                config = json.loads(fixed_json_str)

                if hasattr(self, 'logger'):
                    self.logger.info("Gemini API로 JSON 수정 성공")

                return config
            except json.JSONDecodeError as e:
                error_message = f"수정된 JSON 파싱 실패: {e}"
                if hasattr(self, 'logger'):
                    self.logger.error(error_message)

                # 수정 실패한 JSON 저장
                self._save_failed_json(fixed_json_str, error_message, "gemini_fix")

                return None
            else:
                if hasattr(self, 'logger'):
                    self.logger.error("응답에서 JSON 객체를 찾을 수 없습니다")
                return None

        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"JSON 수정 중 오류 발생: {e}")
            return None
