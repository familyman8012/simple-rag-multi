import streamlit as st
from qa import QASystem
from typing import List, Dict, Any
import pandas as pd
from datetime import datetime
import tempfile
from DocumentLoader import DocumentLoader
import os

def initialize_session_state():
    """세션 상태 초기화"""
    if 'qa_system' not in st.session_state:
        st.session_state.qa_system = QASystem()
    if 'selected_document' not in st.session_state:
        st.session_state.selected_document = None

def format_date(date_str: str) -> str:
    """날짜 포맷팅"""
    try:
        date = datetime.fromisoformat(date_str)
        return date.strftime("%Y-%m-%d")
    except:
        return date_str

def render_document_list(docs: List[Dict[str, Any]], categories: Dict[str, str]):
    """문서 목록 렌더링"""
    if not docs:
        st.info("등록된 문서가 없습니다.")
        return

    # 스타일 적용
    st.markdown("""
        <style>
        .doc-list {
            margin-bottom: 1rem;
        }
        .doc-row {
            padding: 1rem 0;
            border-bottom: 1px solid #eee;
        }
        </style>
    """, unsafe_allow_html=True)

    for doc in docs:
        with st.container():
            cols = st.columns([4, 2, 2, 1])
            
            # 제목과 상세보기 버튼
            with cols[0]:
                st.markdown(f"**{doc['title']}**")
                if st.button("상세보기", key=f"view_{doc['id']}"):
                    st.session_state.selected_document = doc['id']
                    st.rerun()
            
            # 카테고리와 등록일
            with cols[1]:
                st.text(f"카테고리: {categories.get(doc['category'], '일반')}")
                st.text(f"등록일: {format_date(doc['created_at'])}")
                st.text(f"청크 수: {doc['total_chunks']}")
            
            # 카테고리 이동
            with cols[2]:
                new_category = st.selectbox(
                    "이동할 카테고리",
                    options=list(categories.keys()),
                    key=f"cat_{doc['id']}",
                    format_func=lambda x: categories[x]
                )
                if st.button("이동", key=f"move_{doc['id']}", type="primary", use_container_width=True):
                    updates = {"category": new_category}
                    if st.session_state.qa_system.update_document(doc['id'], updates):
                        st.success("카테고리가 변경되었습니다.")
                        st.rerun()
            
            # 삭제 버튼
            with cols[3]:
                if st.button("삭제", key=f"del_{doc['id']}", type="secondary", use_container_width=True):
                    if st.session_state.qa_system.delete_document(doc['id']):
                        st.success("문서가 삭제되었습니다.")
                        st.rerun()

def render_document_detail(doc_id: str, categories: Dict[str, str]):
    """문서 상세 정보 렌더링"""
    doc = st.session_state.qa_system.get_document(doc_id)
    if not doc:
        st.error("문서를 찾을 수 없습니다.")
        return
    
    # 뒤로가기 버튼
    if st.button("← 목록으로"):
        st.session_state.selected_document = None
        st.rerun()
    
    # 문서 기본 정보
    st.header(doc['title'])
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**카테고리**: {categories.get(doc['category'], '일반')}")
        st.markdown(f"**파일명**: {doc['file_name']}")
    with col2:
        st.markdown(f"**등록일**: {format_date(doc['created_at'])}")
        st.markdown(f"**총 청크 수**: {doc['total_chunks']}")
    
    # 청크 목록
    st.subheader("청크 목록")
    chunks = st.session_state.qa_system.list_document_chunks(doc_id)
    
    for chunk in chunks:
        with st.expander(f"청크 {chunk['chunk_index'] + 1}/{doc['total_chunks']}"):
            # 청크 내용 표시
            content = chunk['content']
            edited_content = st.text_area(
                "내용",
                value=content,
                key=f"content_{chunk['id']}",
                height=150
            )
            
            col1, col2 = st.columns(2)
            with col1:
                # 내용 수정 버튼
                if edited_content != content:
                    if st.button("저장", key=f"save_{chunk['id']}", type="primary"):
                        if st.session_state.qa_system.update_chunk(chunk['id'], edited_content):
                            st.success("청크가 수정되었습니다.")
                            st.rerun()
            
            with col2:
                # 청크 삭제 버튼
                if st.button("삭제", key=f"del_chunk_{chunk['id']}", type="secondary"):
                    if st.session_state.qa_system.delete_chunk(chunk['id']):
                        st.success("청크가 삭제되었습니다.")
                        st.rerun()

def render_upload_form(categories: Dict[str, str]):
    """문서 업로드 폼 렌더링"""
    with st.form("upload_form"):
        st.subheader("새 문서 등록")
        
        # 파일 업로드
        uploaded_file = st.file_uploader(
            "파일 선택",
            type=["pdf", "txt", "docx"],
            help="PDF, TXT, DOCX 파일을 지원합니다."
        )
        
        if uploaded_file:
            # 파일명에서 확장자 제거하여 기본 제목으로 설정
            default_title = os.path.splitext(uploaded_file.name)[0]
            title = st.text_input("제목 (선택사항)", value=default_title)
        else:
            title = None
        
        # 카테고리 선택
        category = st.selectbox(
            "카테고리",
            options=list(categories.keys()),
            format_func=lambda x: categories[x]
        )
        
        submitted = st.form_submit_button("등록")
        
        if submitted and uploaded_file:
            with st.spinner("문서 처리 중..."):
                with tempfile.NamedTemporaryFile(
                    delete=False, 
                    suffix=f'.{uploaded_file.name.split(".")[-1]}'
                ) as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    file_path = tmp_file.name

                try:
                    loader = DocumentLoader()
                    chunks = loader.process_document(file_path)
                    
                    metadata = {
                        "title": title or default_title,
                        "category": category,
                        "created_at": datetime.now().isoformat(),
                        "original_filename": uploaded_file.name
                    }
                    
                    st.session_state.qa_system.add_documents(chunks, metadata=metadata)
                    st.success("문서가 등록되었습니다.")
                    st.rerun()
                except Exception as e:
                    st.error(f"문서 처리 중 오류가 발생했습니다: {str(e)}")

def main():
    st.title("문서 관리")
    
    initialize_session_state()
    categories = st.session_state.qa_system.category_config.list_categories()
    
    # 선택된 문서가 있으면 상세 페이지 표시
    if st.session_state.selected_document:
        render_document_detail(st.session_state.selected_document, categories)
        return
    
    # 문서 목록 페이지
    tab1, tab2 = st.tabs(["📚 문서 목록", "📝 새 문서 등록"])
    
    with tab1:
        # 카테고리 필터
        selected_category = st.selectbox(
            "카테고리 필터",
            options=['전체'] + list(categories.keys()),
            format_func=lambda x: '전체' if x == '전체' else categories[x]
        )
        
        # 문서 목록 가져오기
        docs = st.session_state.qa_system.list_documents(
            None if selected_category == '전체' else selected_category
        )
        
        # 문서 목록 렌더링
        render_document_list(docs, categories)
    
    with tab2:
        render_upload_form(categories)

if __name__ == "__main__":
    main()
