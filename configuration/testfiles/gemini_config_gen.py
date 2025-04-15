import os
import json
import argparse
import google.generativeai as genai
from dotenv import load_dotenv

class GeminiConfigGenerator:
    def __init__(self, api_key=None):
        load_dotenv()
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")
            
        genai.configure(api_key=self.api_key)
        
        # 지원되는 모델로 변경 (gemini-1.5-flash 또는 gemini-1.0-pro)
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

    def generate_config(self, task_description):
        prompt = f"""
        다음 작업 설명을 바탕으로 Selenium 자동화 설정 파일을 JSON 형식으로 생성해주세요.
        반드시 다음 구조를 준수해야 합니다:
        
        {json.dumps(self.config_template, indent=2, ensure_ascii=False)}
        
        작업 설명: {task_description}
        
        중요한 주의사항:
        1. targets 배열에는 최소 1개 이상의 작업 단계를 포함해야 합니다
        2. 각 액션은 유효한 Selenium 명령어를 사용해야 합니다
        3. CSS 선택자를 우선적으로 사용해야 합니다
        4. 한국어 요소명을 정확하게 번역해야 합니다
        5. 반드시 유효한 JSON 형식이어야 합니다
        """
        
        try:
            response = self.model.generate_content(prompt)
            return self._extract_and_validate_config(response.text)
        except Exception as e:
            print(f"Gemini API 호출 중 오류 발생: {e}")
            return self.config_template
            
    def _extract_and_validate_config(self, raw_text):
        """텍스트에서 JSON 부분 추출 및 검증"""
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
            return self.config_template

def get_available_models():
    """사용 가능한 Gemini 모델 목록 확인"""
    try:
        models = genai.list_models()
        print("사용 가능한 모델:")
        for model in models:
            if "gemini" in model.name.lower():
                print(f" - {model.name}")
        return [model.name for model in models if "gemini" in model.name.lower()]
    except Exception as e:
        print(f"모델 목록 가져오기 실패: {e}")
        return []

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True, help="자동화 작업 설명")
    parser.add_argument("--output", default="gemini_generated_config.json", help="출력 파일 경로")
    parser.add_argument("--api-key", help="Gemini API 키")
    parser.add_argument("--list-models", action="store_true", help="사용 가능한 모델 목록 표시")
    
    args = parser.parse_args()
    
    if args.list_models:
        # API 키 설정
        api_key = args.api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("GEMINI_API_KEY가 설정되지 않았습니다.")
            exit(1)
            
        genai.configure(api_key=api_key)
        get_available_models()
        exit(0)
    
    generator = GeminiConfigGenerator(api_key=args.api_key)
    config = generator.generate_config(args.task)
    
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"생성된 설정 파일: {args.output}")
