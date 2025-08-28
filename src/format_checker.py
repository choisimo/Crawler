import os
import re
import json
import string
from datetime import datetime


class EnhancedSafeFormatter(string.Formatter):
    """누락된 키를 원본 문자열로 유지하는 커스텀 포맷터"""

    def __init__(self):
        super().__init__()
        self.valid_keys = {
            "task_description", "config_template",
            "valid_selector_types", "valid_action_types"
        }

    def get_value(self, key, args, kwargs):
        if isinstance(key, int):
            return super().get_value(key, args, kwargs)
        if key in self.valid_keys and key in kwargs:
            return kwargs[key]
        if key == 'current_date':
            return datetime.now().strftime('%Y-%m-%d')
        return f'{{{key}}}'

    def format_field(self, value, format_spec):
        try:
            return super().format_field(value, format_spec)
        except ValueError:
            return str(value)

    @staticmethod
    def is_valid_url(url):
        """향상된 URL 유효성 검사"""
        if not url:
            return False, None
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"https://{url}"
        pattern = re.compile(
            r'^(https?://)'
            r'([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
            r'(:\d+)?'
            r'(/.*)?$'
        )
        return bool(pattern.match(url)), url

    def _create_fallback_prompt(self, task_description, original_prompt):
        """포맷팅 실패 시 대체 프롬프트 생성"""
        try:
            urls = re.findall(r'https?://[^\s"\'<>]+', original_prompt or "")
            url_text = "\n".join([f"- {url}" for url in urls]) if urls else "URL이 지정되지 않았습니다."
            safe_text = re.sub(r'[{}]', '', original_prompt or "")
            if len(safe_text) > 500:
                safe_text = safe_text[:500] + "..."
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
            if hasattr(self, 'logger'):
                self.logger.error(f"대체 프롬프트 생성 실패: {e}", exc_info=True)
            return None

    def _preprocess_prompt(self, prompt):
        if not prompt:
            return prompt
        prompt = re.sub(r'(\[)(\s*)(https?://[^"\]\s]+)(\s*)(\])', r'\1\2"\3"\4\5', prompt)
        prompt = self._escape_json_in_prompt(prompt)
        return prompt

    def _escape_json_in_prompt(self, text):
        json_blocks = re.finditer(r'``````', text)
        result = text
        offset = 0
        for match in json_blocks:
            block_start = match.start(1) + offset
            block_end = match.end(1) + offset
            json_content = result[block_start:block_end]
            escaped_content = json_content.replace('{', '{{').replace('}', '}}')
            result = result[:block_start] + escaped_content + result[block_end:]
            offset += len(escaped_content) - len(json_content)
        return result

    def _escape_format_specifiers(self, text):
        if not text:
            return text
        valid_keys = [
            "task_description",
            "config_template",
            "valid_selector_types",
            "valid_action_types"
        ]
        text = text.replace("{{", "___DOUBLE_OPEN___").replace("}}", "___DOUBLE_CLOSE___")
        pattern = r'\{(' + '|'.join(valid_keys) + r')(?:\:[^}]*)?\}'
        placeholder_map = {}

        def replace_valid_key(match):
            token = f"___VALID_KEY_{len(placeholder_map)}___"
            placeholder_map[token] = match.group(0)
            return token

        text = re.sub(pattern, replace_valid_key, text)
        text = text.replace("{", "{{").replace("}", "}}")
        for token, original in placeholder_map.items():
            text = text.replace(token, original)
        text = text.replace("___DOUBLE_OPEN___", "{{").replace("___DOUBLE_CLOSE___", "}}")
        return text

    def _extract_search_term(self, task_description):
        search_match = re.search(r"['\"](.*?)['\"]", task_description)
        if search_match:
            return search_match.group(1)
        search_after = re.search(r"검색\s*[:\-]?\s*(\S+)", task_description)
        if search_after:
            return search_after.group(1)
        search_eng = re.search(r"search\s*[:\-]?\s*(\S+)", task_description, re.IGNORECASE)
        if search_eng:
            return search_eng.group(1)
        return None

    # The methods below are used by other modules (e.g., GeminiApi)
    def _fix_url(self, url):
        if url and not url.startswith('http://') and not url.startswith('https://'):
            return f'https://{url}'
        return url

