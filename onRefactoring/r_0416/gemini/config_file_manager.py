#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
json file 검증 및 fix 스크립트
"""

from gemini_config_gen import GeminiConfigGenerator
class ConfigFileManager:
    def __init__(self, temp_dir=None):
        self.temp_dir = temp_dir or os.getcwd()
        
    def load_config(self, file_path):
        """기존 설정 파일 로드 및 기본 검증"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            # 필수 필드 검증
            required_fields = ['targetUrl', 'targets']
            for field in required_fields:
                if field not in config:
                    raise ValueError(f"필수 필드 누락: {field}")
                    
            return config
        except Exception as e:
            raise RuntimeError(f"파일 로드 실패: {e}")

    def save_revision(self, config, revision_num):
        """수정본 버전 관리 저장"""
        revisions_dir = os.path.join(self.temp_dir, 'revisions')
        os.makedirs(revisions_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'config_rev_{revision_num}_{timestamp}.json'
        path = os.path.join(revisions_dir, filename)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
            
        return path


class ConfigValidator(GeminiConfigGenerator):
    def iterative_fix(self, initial_config, max_attempts=5):
        """점진적 설정 파일 개선 프로세스"""
        current_config = initial_config.copy()
        file_manager = ConfigFileManager(self.temp_dir)
        
        for attempt in range(1, max_attempts+1):
            # 1단계: 기본 검증
            is_valid, issues = self.validate_config(current_config)
            
            if is_valid:
                print(f"✅ [{attempt}/{max_attempts}] 유효한 설정 파일 확인")
                return current_config
                
            # 2단계: 문제점 분석
            print(f"🔧 [{attempt}/{max_attempts}] 문제 수정 시도 중...")
            analysis = self.analyze_issues(current_config, issues)
            
            # 3단계: Gemini 기반 수정
            fixed_config = self.fix_with_feedback(current_config, analysis)
            file_manager.save_revision(fixed_config, attempt)
            
            # 4단계: 수정본 적용
            current_config = fixed_config
            
        return current_config  # 최종 버전 반환

    def analyze_issues(self, config, issues):
        """문제점 심층 분석"""
        analysis = {
            'structure_issues': [],
            'selector_issues': [],
            'action_issues': []
        }
        
        # 문제 분류
        for issue in issues:
            if '셀렉터' in issue:
                analysis['selector_issues'].append(issue)
            elif '액션' in issue:
                analysis['action_issues'].append(issue)
            else:
                analysis['structure_issues'].append(issue)
                
        # 심각도 평가
        severity = 'HIGH' if len(analysis['structure_issues']) > 0 else 'MEDIUM'
        analysis['severity'] = severity
        
        return analysis

    def fix_with_feedback(self, config, analysis):
        """Gemini를 이용한 컨텍스트 보존 수정"""
        prompt = f"""다음 웹 자동화 설정 파일을 수정하세요. 문제 분석 결과와 원본 구조를 유지해야 합니다.
        
        [원본 설정]
        {json.dumps(config, indent=2, ensure_ascii=False)}
        
        [발견된 문제점]
        {analysis}
        
        [수정 요구사항]
        1. 구조적 문제({analysis['severity']} 우선순위) 해결
        2. 셀렉터 오류 수정 시 원본 로직 유지
        3. 액션 순서 변경 없이 구문만 교정
        4. 누락된 필드는 원본 데이터 참조하여 추가
        5. JSON 형식 엄격 준수
        """
        
        response = self.model.generate_content(prompt)
        return self._extract_and_validate_config(response.text)
