#!/usr/bin/env python3
import os
import json
import argparse
import re
import google.generativeai as genai
from dotenv import load_dotenv
import string
import logging
from datetime import datetime
import sys
import config_file_manager

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

class GeminiConfigGenerator:
    def __init__(self, api_key=None, max_retries=5, verbose=False, temp_dir=None):
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
            print(f"설정 파일 생성 시도 중... (시도 {attempt+1}/{self.max_retries})")
            
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

    def _extract_and_validate_config(self, raw_text):
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

    def _create_default_config(self, task_description):
        """안전한 기본 설정 파일 생성"""
        default_config = self.config_template.copy()
        
        if self.user_url:
            default_config["targetUrl"] = self.user_url
            if default_config.get("targets"):
                default_config["targets"][0]["url"] = self.user_url

        # URL 강제 설정
        if hasattr(self, 'user_url') and self.user_url:
            default_config["targetUrl"] = self.user_url
            default_config["targets"][0]["url"] = self.user_url  # 타겟 URL도 동시 업데이트
        
        return default_config

    def _add_naver_config(self, config, task_description, is_search=True):
        # 검색어 추출
        search_term = self._extract_search_term(task_description) or "검색어"
        
        config["targets"] = [{
            "name": f"네이버 {search_term} 검색 및 데이터 추출",
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

    def _add_google_config(self, config, task_description, is_search=True):
        # 검색어 추출
        search_term = self._extract_search_term(task_description) or "검색어"
        
        config["targets"] = [{
            "name": f"구글 {search_term} 검색 및 데이터 추출",
            "url": "https://www.google.com",
            "wait_for": {
                "type": "name",
                "value": "q",
                "timeout": 10
            },
            "actions": [
                {
                    "type": "input",
                    "selector": {
                        "type": "name",
                        "value": "q"
                    },
                    "text": search_term,
                    "submit": True
                },
                {
                    "type": "wait",
                    "seconds": 3
                },
                {
                    "type": "screenshot",
                    "filename": "google_search_results.png"
                },
                {
                    "type": "extract",
                    "selector": {
                        "type": "css",
                        "value": "h3"
                    },
                    "save": True,
                    "output_file": f"{search_term}_google_results.txt"
                }
            ]
        }]

    def _add_generic_config(self, config, task_description, url, is_search=False, is_data_extraction=False, is_form=False):
        
        if "targets" not in config or not config["targets"]:
            config["targets"] = [{
            "name": "새 작업",
            "url": config.get("targetUrl", "https://example.com"),
            "actions": []
        }]
        
        #  작업 이름 구성
        config["targets"][0]["url"] = config["targetUrl"] 
        site_name = re.search(r'https?://(?:www\.)?([^/]+)', url)
        site_name = site_name.group(1) if site_name else "웹사이트"
        
        actions = []
        
        # 페이지 스크린샷은 기본 작업
        actions.append({
            "type": "screenshot",
            "filename": f"{site_name}_screenshot.png"
        })
        
        # 검색 기능이 필요한 경우
        if is_search:
            search_term = self._extract_search_term(task_description) or "검색어"
            actions.insert(0, {
                "type": "input",
                "selector": {
                    "type": "css",
                    "value": "input[type='text'], input[type='search'], .search-input"
                },
                "text": search_term,
                "submit": False
            })
            actions.insert(1, {
                "type": "click",
                "selector": {
                    "type": "css",
                    "value": "button[type='submit'], .search-button, input[type='submit']"
                }
            })
            actions.insert(2, {
                "type": "wait",
                "seconds": 3
            })
        
        # 데이터 추출이 필요한 경우
        if is_data_extraction:
            actions.append({
                "type": "extract",
                "selector": {
                    "type": "css",
                    "value": "h1, h2, h3, .title, .item-title"
                },
                "save": True,
                "output_file": f"{site_name}_extracted_data.txt"
            })
        
        # 양식 제출이 필요한 경우
        if is_form:
            # 작업 조정 (구체적인 양식 필드는 사이트마다 다름)
            actions = [
                {
                    "type": "input",
                    "selector": {
                        "type": "css",
                        "value": "input[type='text'], .form-control"
                    },
                    "text": "샘플 텍스트",
                    "submit": False
                },
                {
                    "type": "click",
                    "selector": {
                        "type": "css", 
                        "value": "button[type='submit'], input[type='submit']"
                    }
                },
                {
                    "type": "wait",
                    "seconds": 3
                    },
                    {
                        "type": "screenshot",
                        "filename": f"{site_name}_form_submitted.png"
                    }
                ]
            
        config["targets"] = [{
            "name": f"{site_name} 자동화",
            "url": self.target_url if hasattr(self, 'target_url') and self.target_url else "https://www.example.com",
            "wait_for": {
                "type": "tag_name",
                "value": "body",
                "timeout": 10
            },
            "actions": actions
        }]

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
                issues.append(f"대상 #{target_idx+1}에 이름이 없습니다")
            
            if "url" not in target:
                issues.append(f"대상 #{target_idx+1}에 URL이 없습니다")
            
            if "actions" not in target or not target["actions"]:
                issues.append(f"대상 #{target_idx+1}에 액션이 없습니다")
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
        
        # 셀렉터 타입 검사 추가
        if isinstance(selector, str):
            issues.append(f"대상 #{target_idx+1}, 액션 #{action_idx+1}의 셀렉터가 객체가 아닌 문자열입니다: {selector}")
            return issues
        
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
                context_before = json_str[max(0, 86-30):86]
                problematic_char = json_str[86] if 86 < len(json_str) else "EOF"
                context_after = json_str[87:min(len(json_str), 86+30)] if 87 < len(json_str) else ""
                
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

    def _fix_url(self, url):
        if url and not url.startswith('http://') and not url.startswith('https://'):
            return f'https://{url}'
        return url


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gemini API를 이용한 Selenium 설정 파일 생성")
    parser.add_argument("--task", required=True, help="자동화 작업 설명")
    parser.add_argument("--output", default="gemini_generated_config.json", help="출력 파일 경로")
    parser.add_argument("--api-key", help="Gemini API 키")
    parser.add_argument("--max-retries", type=int, default=5, help="최대 시도 횟수")
    parser.add_argument("--validate-only", action="store_true", help="기존 설정 파일만 검증")
    parser.add_argument("--prompt", help="사용자 정의 프롬프트 파일 경로")
    parser.add_argument("--verbose", "-v", action="store_true", help="상세 로깅 활성화")
    parser.add_argument("--url", help="타겟 사이트의 URL (예: https://example.com)")
    parser.add_argument("--fix", help="기존 설정 파일 수정 모드")
    parser.add_argument("--max-fix-attempts", type=int, default=5, 
                   help="최대 수정 시도 횟수")

    args = parser.parse_args()
    print(f"input arguments : ${args}")
    # GeminiConfigGenerator 인스턴스 생성 (올바른 문법)
    config_gen = GeminiConfigGenerator(api_key=args.api_key, max_retries=args.max_retries)

    # 프롬프트 파일 처리
    custom_prompt = None
    if args.prompt and os.path.exists(args.prompt):
        try:
            with open(args.prompt, 'r', encoding='utf-8') as f:
                custom_prompt = f.read()
        except Exception as e:
            print(f"프롬프트 파일 로드 중 오류: {e}")
    
    # 설정 파일 생성
    config = config_gen.generate_config(args.task, custom_prompt, args.url)
    
    # URL이 제공되었으나 설정에 없는 경우 추가
    if args.url and "targetUrl" not in config:
        config["targetUrl"] = args.url
    
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


    if args.fix:
        file_manager = config_file_manager.ConfigFileManager()
        print(f"🔍 설정 파일 수정 모드 시작: {args.fix}")
    
        validator = ConfigValidator(api_key=args.api_key)
    
        try:
            original_config = file_manager.load_config(args.fix)
            fixed_config = validator.iterative_fix(original_config, args.max_fix_attempts)
            
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(fixed_config, f, indent=2, ensure_ascii=False)
                
            print(f"✅ 수정 완료: {args.output}")
        except Exception as e:
            print(f"❌ 수정 실패: {e}")

    
    print(f"생성된 설정 파일: {args.output}")
