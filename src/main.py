import os
import json
import argparse
from config_file_manager import ConfigFileManager, ConfigValidator
from gemini_api import GeminiApi as GeminiConfigGenerator

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
    print(f"input arguments : {args}")
    config_gen = GeminiConfigGenerator(api_key=args.api_key, max_retries=args.max_retries)

    custom_prompt = None
    if args.prompt and os.path.exists(args.prompt):
        try:
            with open(args.prompt, 'r', encoding='utf-8') as f:
                custom_prompt = f.read()
        except Exception as e:
            print(f"프롬프트 파일 로드 중 오류: {e}")

    config = config_gen.generate_config(args.task, custom_prompt, args.url)

    if args.url and "targetUrl" not in config:
        config["targetUrl"] = args.url

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    if args.fix:
        file_manager = ConfigFileManager()
        print(f"설정 파일 수정 모드 시작: {args.fix}")

        validator = ConfigValidator(api_key=args.api_key)

        try:
            original_config = file_manager.load_config(args.fix)
            fixed_config = validator.iterative_fix(original_config, args.max_fix_attempts)

            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(fixed_config, f, indent=2, ensure_ascii=False)

            print(f"수정 완료: {args.output}")
        except Exception as e:
            print(f"수정 실패: {e}")

    print(f"생성된 설정 파일: {args.output}")
