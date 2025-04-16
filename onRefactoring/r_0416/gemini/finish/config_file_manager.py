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

        for attempt in range(1, max_attempts + 1):
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


class ConfigGenerator:
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

    def _add_generic_config(self, config, task_description, url, is_search=False, is_data_extraction=False,
                            is_form=False):

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
