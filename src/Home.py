import streamlit as st
from qa import QASystem
from typing import List, Dict, Any

def initialize_session_state():
    """세션 상태 초기화"""
    if 'qa_system' not in st.session_state:
        st.session_state.qa_system = QASystem()
    if 'current_category' not in st.session_state:
        st.session_state.current_category = 'general'
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []

def main():
    st.title("문서 기반 질의응답 시스템")
    
    # 세션 상태 초기화
    initialize_session_state()
    
    # 사이드바 - 카테고리 필터
    categories = st.session_state.qa_system.category_config.list_categories()
    with st.sidebar:
        st.header("검색 설정")
        selected_category = st.selectbox(
            "카테고리 필터",
            options=list(categories.keys()),
            format_func=lambda x: categories[x],
            key='current_category'
        )
        
        # 카테고리 자동 감지 옵션
        auto_detect = st.checkbox("카테고리 자동 감지", value=True)
        
        # 검색 설정 설명
        st.info("""
        💡 **카테고리 필터**를 사용하면 특정 카테고리의 문서만 검색합니다.
        
        💡 **카테고리 자동 감지**를 켜면 질문의 내용에 따라 자동으로 관련된 카테고리를 찾습니다.
        """)
        
        # DB 관리 링크
        st.divider()
        st.markdown("""
        📚 문서를 추가하거나 관리하려면 [DB 관리 페이지](/DB_Management)를 이용하세요.
        """)
    
    # 메인 영역 - 채팅 스타일의 Q&A
    # 이전 대화 내역 표시
    for qa in st.session_state.chat_history:
        with st.chat_message("user"):
            st.write(qa["question"])
        with st.chat_message("assistant"):
            st.write(qa["answer"])
            if qa.get("references"):
                st.markdown("---")
                st.markdown("**참고 문서:**")
                for ref in qa["references"]:
                    st.markdown(f"- {ref['title']} (유사도: {ref['similarity']:.2f})")
    
    # 새로운 질문 입력
    question = st.chat_input("문서에 대해 질문해 보세요")
    if question:
        with st.chat_message("user"):
            st.write(question)
        
        with st.chat_message("assistant"):
            with st.spinner("답변 생성 중..."):
                try:
                    # 카테고리 자동 감지 여부에 따라 카테고리 설정
                    category = None if auto_detect else selected_category
                    
                    # 질문에 대한 답변 생성
                    result = st.session_state.qa_system.ask(question, category=category)
                    
                    # 답변 표시
                    st.write(result["answer"])
                    
                    # 참조 문서 정보 표시
                    if result.get("documents"):
                        st.markdown("---")
                        st.markdown("**참고 문서:**")
                        for doc in result["documents"]:
                            st.markdown(f"- {doc['title']} (유사도: {doc['similarity']:.2f})")
                    
                    # 대화 내역에 추가
                    st.session_state.chat_history.append({
                        "question": question,
                        "answer": result["answer"],
                        "references": result.get("documents", [])
                    })
                    
                except Exception as e:
                    st.error(f"답변 생성 중 오류가 발생했습니다: {str(e)}")

if __name__ == "__main__":
    main()
