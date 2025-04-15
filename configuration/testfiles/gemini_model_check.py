import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("GEMINI_API_KEY가 설정되지 않았습니다.")
    exit(1)

genai.configure(api_key=api_key)

# 사용 가능한 모델 목록 출력
models = genai.list_models()
print("사용 가능한 모델:")
for model in models:
    if "gemini" in model.name.lower():
        print(f"- {model.name}")
        print(f"  지원 메서드: {model.supported_generation_methods}")
        print()
