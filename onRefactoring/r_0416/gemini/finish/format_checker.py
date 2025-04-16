class EnhancedSafeFormatter(string.Formatter):
    """누락된 키를 원본 문자열로 유지하는 커스텀 포맷터"""

    def __init__(self):
        super().__init__()
        # 허용된 포맷 키
        self.valid_keys = {
            "task_description", "config_template",
            "valid_selector_types", "valid_action_types"
        }

    def get_value(self, key, args, kwargs):
        # 키가 숫자(위치 인자)인 경우
        if isinstance(key, int):
            return super().get_value(key, args, kwargs)

        # 키가 유효한 포맷 변수인 경우
        if key in self.valid_keys and key in kwargs:
            return kwargs[key]

        # 미리 정의된 특수 키 처리
        if key == 'current_date':
            from datetime import datetime
            return datetime.now().strftime('%Y-%m-%d')

        # 기타 모든 경우: 원본 형태로 유지
        return f'{{{key}}}'

    def format_field(self, value, format_spec):
        # 복잡한 포맷 스펙 처리
        try:
            return super().format_field(value, format_spec)
        except ValueError:
            # 포맷 스펙 오류 시 기본 문자열 변환
            return str(value)

    def is_valid_url(url):
        """향상된 URL 유효성 검사"""
        import re

        # URL이 없는 경우
        if not url:
            return False, None

        # 프로토콜이 없는 경우 자동으로 https:// 추가
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"https://{url}"

        # 정규식 패턴으로 유효성 검사
        pattern = re.compile(
            r'^(https?://)'  # http:// 또는 https://
            r'([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'  # 도메인
            r'(:\d+)?'  # 포트 (선택)
            r'(/.*)?$'  # 경로 (선택)
        )

        return bool(pattern.match(url)), url

    def _create_fallback_prompt(self, task_description, original_prompt):
        """포맷팅 실패 시 대체 프롬프트 생성"""
        try:

            site_url = None
            if self.user_url is None:
                # URL 추출
                urls = re.findall(r'https?://[^\s"\'<>]+', original_prompt)
                url_text = "\n".join([f"- {url}" for url in urls]) if urls else "URL이 지정되지 않았습니다."
                if is_valid_url(url_text) is False:
                    print("invalid url")
            else:
                site_url = self.user_url

                # 텍스트 중 일부 추출 (중괄호 제외)
            safe_text = re.sub(r'[{}]', '', original_prompt)
            # 처음 500자만 사용
            if len(safe_text) > 500:
                safe_text = safe_text[:500] + "..."

            # 안전한 프롬프트 구성
            return f"""
            다음 작업 설명과 관련 정보를 바탕으로 Selenium 자동화 설정 파일을 JSON 형식으로 생성해주세요.

            작업 설명: {task_description}

            관련 URL:
            {url_text}

            작업 컨텍스트:
            {safe_text}

            설정 파일 구조는 다음과 같아야 합니다:
            {json.dumps(self.config_template, indent=2, ensure_ascii=False)}

            중요한 주의사항:
            1. targets 배열에는 최소 1개 이상의 작업 단계를 포함해야 합니다
            2. 각 액션은 유효한 Selenium 명령어를 사용해야 합니다
            3. 모든 selectors는 반드시 유효한 값을 포함해야 합니다
            4. 응답은 반드시 유효한 JSON 형식이어야 합니다
            """
        except Exception as e:
            self.logger.error(f"대체 프롬프트 생성 실패: {e}", exc_info=True)
            return None

    def _preprocess_prompt(self, prompt):
        """프롬프트 내용 전처리"""
        if not prompt:
            return prompt

        # 1. URL 패턴 특별 처리 (큰따옴표로 감싸기)
        prompt = re.sub(r'(\[)(\s*)(https?://[^"\]\s]+)(\s*)(\])',
                        r'\1\2"\3"\4\5', prompt)

        # 2. JSON 형식 내 중괄호 이스케이프
        prompt = self._escape_json_in_prompt(prompt)

        return prompt

    def _escape_json_in_prompt(self, text):
        """프롬프트 내 JSON 예시 부분의 중괄호 이스케이프 처리"""
        # JSON 블록 감지 (예: ``````)
        json_blocks = re.finditer(r'``````', text)

        result = text
        offset = 0

        for match in json_blocks:
            block_start = match.start(1) + offset
            block_end = match.end(1) + offset

            # 블록 내용 추출 및 중괄호 이스케이프
            json_content = result[block_start:block_end]
            escaped_content = json_content.replace('{', '{{').replace('}', '}}')

            # 원본을 이스케이프된 내용으로 교체
            result = result[:block_start] + escaped_content + result[block_end:]

            # 다음 검색을 위한 오프셋 조정
            offset += len(escaped_content) - len(json_content)

        return result

    def _escape_format_specifiers(self, text):
        """프롬프트 내 포맷 지정자 이스케이프 처리"""
        if not text:
            return text

        # 이미 이스케이프된 중괄호는 건너뛰고 단일 중괄호만 이스케이프
        # 단, 올바른 포맷 지정자({task_description}, {config_template} 등)는 보존

        # 알려진 유효 키 패턴
        valid_keys = [
            "task_description",
            "config_template",
            "valid_selector_types",
            "valid_action_types"
        ]

        # 정규 표현식으로 유효하지 않은 중괄호만 이스케이프
        import re

        # 1. 먼저 이미 이스케이프된 중괄호를 임시 토큰으로 대체
        text = text.replace("{{", "___DOUBLE_OPEN___").replace("}}", "___DOUBLE_CLOSE___")

        # 2. 유효한 포맷 키를 임시 토큰으로 대체
        pattern = r'\{(' + '|'.join(valid_keys) + r')(?:\:[^}]*)?\}'
        placeholder_map = {}

        def replace_valid_key(match):
            token = f"___VALID_KEY_{len(placeholder_map)}___"
            placeholder_map[token] = match.group(0)
            return token

        text = re.sub(pattern, replace_valid_key, text)

        # 3. 남아있는 단일 중괄호 이스케이프
        text = text.replace("{", "{{").replace("}", "}}")

        # 4. 임시 토큰 복원
        for token, original in placeholder_map.items():
            text = text.replace(token, original)

        text = text.replace("___DOUBLE_OPEN___", "{{").replace("___DOUBLE_CLOSE___", "}}")

        return text

    def _extract_search_term(self, task_description):
        """작업 설명에서 검색어 추출"""
        # 따옴표로 둘러싸인 검색어 추출 시도
        search_match = re.search(r"['\"](.*?)['\"]", task_description)
        if search_match:
            return search_match.group(1)

        # '검색' 단어 이후의 단어 추출 시도
        search_after = re.search(r"검색\s*[:\-]?\s*(\S+)", task_description)
        if search_after:
            return search_after.group(1)

        # 영어 'search' 단어 이후의 단어 추출 시도
        search_eng = re.search(r"search\s*[:\-]?\s*(\S+)", task_description, re.IGNORECASE)
        if search_eng:
            return search_eng.group(1)

        return None

    def validate_config(self, config):
        """설정 파일의 모든 셀렉터와 액션 유효성 검사"""
        issues = []

        # URL 검증 및 수정
        if "targetUrl" in config:
            url = config["targetUrl"]
            if not url.startswith("http://") and not url.startswith("https://"):
                config["targetUrl"] = f"https://{url}"
                if hasattr(self, 'logger'):
                    self.logger.info(f"targetUrl 프로토콜 자동 추가: {config['targetUrl']}")
        elif hasattr(self, 'user_url') and self.user_url:
            config["targetUrl"] = self._fix_url(self.user_url)
            if hasattr(self, 'logger'):
                self.logger.info(f"targetUrl 필드 추가: {config['targetUrl']}")

        # 대상 검증
        if not config.get("targets") or len(config["targets"]) == 0:
            issues.append("최소 하나 이상의 대상이 필요합니다")
            return False, issues

        # 각 대상 검증
        for target_idx, target in enumerate(config["targets"]):
            # 필수 필드 검증
            if "name" not in target:
                issues.append(f"대상 #{target_idx + 1}에 이름이 없습니다")

            if "url" not in target:
                issues.append(f"대상 #{target_idx + 1}에 URL이 없습니다")

            if "actions" not in target or not target["actions"]:
                issues.append(f"대상 #{target_idx + 1}에 액션이 없습니다")
                continue

            # 각 액션 검증
            for action_idx, action in enumerate(target["actions"]):
                if "selector" in action and isinstance(action["selector"], str):
                    selector_value = action["selector"]
                    action["selector"] = {
                        "type": "css",  # 기본 타입으로 CSS 사용
                        "value": selector_value
                    }
                    if hasattr(self, 'logger'):
                        self.logger.info(f"문자열 셀렉터를 자동으로 객체 형식으로 변환: {selector_value}")
                if "type" not in action:
                    issues.append(f"대상 #{target_idx + 1}, 액션 #{action_idx + 1}에 타입이 없습니다")
                    continue

                action_type = action["type"].lower()

                # 액션 타입 검증
                if action_type not in self.valid_action_types:
                    issues.append(f"대상 #{target_idx + 1}, 액션 #{action_idx + 1}의 타입이 잘못되었습니다: {action_type}")

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
            issues.append(f"대상 #{target_idx + 1}, 액션 #{action_idx + 1}에 셀렉터가 없습니다")
            return issues

        selector = action["selector"]

        # 셀렉터 타입 검사 추가
        if isinstance(selector, str):
            issues.append(f"대상 #{target_idx + 1}, 액션 #{action_idx + 1}의 셀렉터가 객체가 아닌 문자열입니다: {selector}")
            return issues

        # 셀렉터 타입 확인
        if "type" not in selector:
            issues.append(f"대상 #{target_idx + 1}, 액션 #{action_idx + 1}의 셀렉터에 타입이 없습니다")
        elif selector["type"] not in self.valid_selector_types:
            issues.append(f"대상 #{target_idx + 1}, 액션 #{action_idx + 1}의 셀렉터 타입이 잘못되었습니다: {selector['type']}")

        # 셀렉터 값 확인
        if "value" not in selector:
            issues.append(f"대상 #{target_idx + 1}, 액션 #{action_idx + 1}의 셀렉터에 값이 없습니다")
        elif not selector["value"] or len(selector["value"].strip()) == 0:
            issues.append(f"대상 #{target_idx + 1}, 액션 #{action_idx + 1}의 셀렉터 값이 비어 있습니다")

        # 셀렉터 문법 검증
        if "type" in selector and "value" in selector:
            selector_type = selector["type"]
            selector_value = selector["value"]

            if selector_type == "css":
                # CSS 선택자 형식 검증
                if self._has_invalid_css_syntax(selector_value):
                    issues.append(f"대상 #{target_idx + 1}, 액션 #{action_idx + 1}의 CSS 선택자 구문이 잘못되었습니다: {selector_value}")

            elif selector_type == "xpath":
                # XPath 형식 검증
                if self._has_invalid_xpath_syntax(selector_value):
                    issues.append(
                        f"대상 #{target_idx + 1}, 액션 #{action_idx + 1}의 XPath 선택자 구문이 잘못되었습니다: {selector_value}")

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

    def _save_failed_json(self, json_str, error_message, stage="parsing"):
        """실패한 JSON을 파일로 저장하여 디버깅 지원"""
        # 저장 디렉토리 생성
        failed_dir = os.path.join(self.temp_dir, 'failed')
        os.makedirs(failed_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 실패한 JSON 저장
        json_file_path = os.path.join(failed_dir, f'failed_{stage}_{timestamp}.json')
        with open(json_file_path, 'w', encoding='utf-8') as f:
            f.write(json_str)

        # 오류 정보 저장
        error_file_path = os.path.join(failed_dir, f'error_{stage}_{timestamp}.txt')
        with open(error_file_path, 'w', encoding='utf-8') as f:
            f.write(f"Error: {error_message}\n\n")

            # 86번째 컬럼 근처 내용 분석 (JSON 파싱 오류 시)
            if "column 86" in error_message and len(json_str) > 86:
                context_before = json_str[max(0, 86 - 30):86]
                problematic_char = json_str[86] if 86 < len(json_str) else "EOF"
                context_after = json_str[87:min(len(json_str), 86 + 30)] if 87 < len(json_str) else ""

                f.write("========== 오류 발생 위치 분석 ==========\n")
                f.write(f"이전 컨텍스트: {context_before}\n")
                f.write(f"문제 문자(86번째 컬럼): {problematic_char}\n")
                f.write(f"이후 컨텍스트: {context_after}\n")

        if hasattr(self, 'logger'):
            self.logger.info(f"실패한 JSON 저장: {json_file_path}")
            self.logger.info(f"오류 정보 저장: {error_file_path}")
        else:
            print(f"실패한 JSON 저장: {json_file_path}")
            print(f"오류 정보 저장: {error_file_path}")

        return json_file_path, error_file_path


    def _fix_url(self, url):
        if url and not url.startswith('http://') and not url.startswith('https://'):
            return f'https://{url}'
        return url
