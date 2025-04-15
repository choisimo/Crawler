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
    parser.add_argument("--max-retries", type=int, default=3, help="최대 시도 횟수")
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
