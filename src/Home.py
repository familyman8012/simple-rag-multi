import streamlit as st
from qa import QASystem
from DocumentLoader import DocumentLoader
from typing import List, Dict, Any
import os
import tempfile
from pathlib import Path

def initialize_session_state():
    """세션 상태 초기화"""
    if 'qa_system' not in st.session_state:
        st.session_state.qa_system = QASystem()
    if 'current_category' not in st.session_state:
        st.session_state.current_category = 'general'
    if "document_processed" not in st.session_state:
        st.session_state.document_processed = False
    if "current_file" not in st.session_state:
        st.session_state.current_file = None

def main():
    st.title("문서 기반 질의응답 시스템")
    
    # 세션 상태 초기화
    initialize_session_state()
    
    # 사이드바에 카테고리 선택 추가
    categories = st.session_state.qa_system.category_config.list_categories()
    selected_category = st.sidebar.selectbox(
        "카테고리 선택",
        options=list(categories.keys()),
        format_func=lambda x: categories[x],
        key='current_category'
    )
    
    # 사이드바 - 문서 업로드
    with st.sidebar:
        st.header("문서 업로드")
        uploaded_file = st.file_uploader(
            "파일을 선택하세요",
            type=["pdf", "txt", "docx"],
            help="PDF, TXT, DOCX 파일을 지원합니다.",
            accept_multiple_files=False
        )

        if uploaded_file is not None:
            # 새로운 파일이 업로드되었는지 확인
            if st.session_state.current_file != uploaded_file.name:
                st.session_state.document_processed = False
                st.session_state.current_file = uploaded_file.name

            if st.button("문서 처리 시작"):
                with st.spinner("문서 처리 중..."):
                    # 임시 파일로 저장
                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=f'.{uploaded_file.name.split(".")[-1]}'
                    ) as tmp_file:
                        tmp_file.write(uploaded_file.getvalue())
                        file_path = tmp_file.name

                    try:
                        # 기존 문서 삭제
                        st.session_state.qa_system.vector_store.delete_all()
                        
                        # 새 문서 처리
                        loader = DocumentLoader()
                        chunks = loader.process_document(file_path)
                        
                        # 청크를 벡터 DB에 저장 (선택된 카테고리 사용)
                        st.session_state.qa_system.add_documents(
                            chunks,
                            category=selected_category
                        )
                        st.session_state.document_processed = True
                        st.success("문서 처리가 완료되었습니다!")

                    except Exception as e:
                        st.error(f"문서 처리 중 오류가 발생했습니다: {str(e)}")
                    finally:
                        # 임시 파일 삭제
                        Path(file_path).unlink()

    # 메인 영역 - 질문 입력 및 답변 표시
    if st.session_state.document_processed:
        st.header("질문하기")
        
        # 카테고리 자동 감지 옵션
        auto_detect = st.checkbox("카테고리 자동 감지", value=True)
        
        question = st.text_input("문서에 대해 질문해 보세요")
        if st.button("답변 받기") and question:
            with st.spinner("답변 생성 중..."):
                try:
                    # 카테고리 자동 감지 여부에 따라 카테고리 설정
                    category = None if auto_detect else selected_category
                    
                    answer = st.session_state.qa_system.answer_question(
                        question,
                        category=category
                    )
                    st.write("답변:")
                    st.write(answer)
                except Exception as e:
                    st.error(f"답변 생성 중 오류가 발생했습니다: {str(e)}")
    else:
        st.info("👈 사이드바에서 문서 파일을 업로드하고 처리를 시작해주세요.")

if __name__ == "__main__":
    main()
