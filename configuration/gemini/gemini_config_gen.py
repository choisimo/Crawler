import os
import json
import argparse
import google.generativeai as genai
from dotenv import load_dotenv

class GeminiConfigGenerator:
    def __init__(self, api_key=None):
        load_dotenv()
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        
        # 설정 파일 템플릿
        self.config_template = {
            "browser": {
                "type": "chrome",
                "headless": True,
                "options": [
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--window-size=1920,1080"
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

    def generate_config(self, task_description):
        prompt = f"""
        다음 작업 설명을 바탕으로 Selenium 자동화 설정 파일을 JSON 형식으로 생성해주세요.
        반드시 다음 구조를 준수해야 합니다:
        
        {json.dumps(self.config_template, indent=2, ensure_ascii=False)}
        
        작업 설명: {task_description}
        
        중요한 주의사항:
        1. targets 배열에는 최소 1개 이상의 작업 단계 포함
        2. 각 액션은 유효한 Selenium 명령어 사용
        3. CSS 선택자 우선 사용
        4. 한국어 요소명 정확하게 번역
        """
        
        response = self.model.generate_content(prompt)
        return self._validate_config(response.text)

    def _validate_config(self, raw_config):
        try:
            config = json.loads(raw_config)
            
            # 필수 필드 검증
            required_fields = ['browser', 'targets', 'output', 'timeouts']
            for field in required_fields:
                if field not in config:
                    raise ValueError(f"필수 필드 누락: {field}")
            
            return config
        except json.JSONDecodeError:
            print("잘못된 JSON 형식. 기본 템플릿 사용")
            return self.config_template

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True, help="자동화 작업 설명")
    parser.add_argument("--output", default="gemini_generated_config.json", help="출력 파일 경로")
    parser.add_argument("--api-key", help="Gemini API 키")
    
    args = parser.parse_args()
    
    generator = GeminiConfigGenerator(api_key=args.api_key)
    config = generator.generate_config(args.task)
    
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"생성된 설정 파일: {args.output}")
