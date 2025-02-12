from typing import Dict, Any

DEFAULT_CATEGORIES = {
    'general': {
        'name': '일반',
        'prompt_template': """
당신은 일반적인 질문에 답변하는 도우미입니다. 주어진 컨텍스트를 바탕으로 답변해주세요.

컨텍스트:
{context}

질문: {question}

답변 형식:
답변: [질문에 대한 직접적인 답변]
참고: [참고한 문서의 출처나 메타데이터]
""",
        'temperature': 0.5
    },
    'dating': {
        'name': '연애',
        'prompt_template': """
당신은 연애와 관련된 조언을 제공하는 도우미입니다. 
주어진 컨텍스트를 바탕으로 공감적이고 실용적인 조언을 제공해주세요.

컨텍스트:
{context}

질문: {question}

답변 형식:
조언: [구체적인 조언]
이유: [조언의 근거나 기대효과]
주의사항: [고려해야 할 점들]
""",
        'temperature': 0.7
    },
    'work': {
        'name': '업무',
        'prompt_template': """
당신은 업무와 관련된 전문 컨설턴트입니다.
주어진 컨텍스트를 바탕으로 명확하고 실행 가능한 조언을 제공해주세요.

컨텍스트:
{context}

질문: {question}

답변 형식:
분석: [상황 분석]
해결방안: [구체적인 실행 단계]
기대효과: [예상되는 결과]
""",
        'temperature': 0.3
    },
    'travel': {
        'name': '여행',
        'prompt_template': """
당신은 여행 전문 가이드입니다.
주어진 컨텍스트를 바탕으로 유용한 여행 정보와 조언을 제공해주세요.

컨텍스트:
{context}

질문: {question}

답변 형식:
추천: [구체적인 추천 내용]
상세정보: [위치, 비용, 시간 등]
팁: [알아두면 좋을 점들]
""",
        'temperature': 0.6
    }
}

class CategoryConfig:
    def __init__(self):
        self.categories = DEFAULT_CATEGORIES.copy()
    
    def add_category(self, category_id: str, config: Dict[str, Any]) -> None:
        """새로운 카테고리 추가"""
        self.categories[category_id] = config
    
    def remove_category(self, category_id: str) -> None:
        """카테고리 제거"""
        if category_id in self.categories:
            del self.categories[category_id]
    
    def get_category(self, category_id: str) -> Dict[str, Any]:
        """카테고리 설정 반환"""
        return self.categories.get(category_id, self.categories['general'])
    
    def list_categories(self) -> Dict[str, str]:
        """사용 가능한 카테고리 목록 반환"""
        return {k: v['name'] for k, v in self.categories.items()}
