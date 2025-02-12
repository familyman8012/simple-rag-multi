import os
from typing import List, Dict, Any, Optional
from db import VectorStore
from openai import OpenAI
from embedding_cache import EmbeddingCache
import google.generativeai as genai
from dotenv import load_dotenv
from category_config import CategoryConfig
import re

# .env 파일 로드
load_dotenv()

class QASystem:
    def __init__(self):
        self.vector_store = VectorStore()
        self.category_config = CategoryConfig()
        self.embedding_cache = EmbeddingCache()
        self.model_name = "text-embedding-ada-002"  # OpenAI 임베딩 모델
        self.client = OpenAI()  # OpenAI 클라이언트 초기화

        # OpenAI API 키 확인
        if not os.environ.get("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY가 환경변수에 설정되어 있어야 합니다.")
            
        # Gemini API 키 확인 및 설정
        if not os.environ.get("GEMINI_API_KEY"):
            raise ValueError("GEMINI_API_KEY가 환경변수에 설정되어 있어야 합니다.")
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        
        # Gemini 모델 초기화
        generation_config = {
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
        }
        self.gemini_model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            generation_config=generation_config,
        )
        self.chat_session = None

    def add_documents(
        self, chunks: List[Dict[str, Any]], metadata: Dict[str, Any] = None
    ) -> str:
        """
        문서 추가
        Args:
            chunks: 문서 청크 리스트 ({'content': str})
            metadata: 문서 메타데이터
        Returns:
            생성된 문서 ID
        """
        if metadata is None:
            metadata = {}

        # 각 청크에 대한 임베딩 생성
        processed_chunks = []
        for chunk in chunks:
            content = chunk["content"]

            # 캐시된 임베딩이 있는지 확인
            embedding = self.embedding_cache.get(content, self.model_name)
            if embedding is None:
                # 임베딩 생성 및 캐시
                embedding = self._create_embedding(content)
                self.embedding_cache.set(content, self.model_name, embedding)

            processed_chunks.append({"content": content, "embedding": embedding})

        # 문서와 청크 저장
        return self.vector_store.add_document(processed_chunks, metadata)

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """문서 정보 조회"""
        return self.vector_store.get_document(doc_id)

    def list_documents(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """문서 목록 조회"""
        return self.vector_store.list_documents(category)

    def update_document(self, doc_id: str, updates: Dict[str, Any]) -> bool:
        """문서 정보 업데이트"""
        return self.vector_store.update_document(doc_id, updates)

    def delete_document(self, doc_id: str) -> bool:
        """문서와 관련 청크 모두 삭제"""
        return self.vector_store.delete_document(doc_id)

    def list_document_chunks(self, doc_id: str) -> List[Dict[str, Any]]:
        """특정 문서의 청크 목록 조회"""
        return self.vector_store.list_document_chunks(doc_id)

    def update_chunk(self, chunk_id: str, content: str) -> bool:
        """청크 내용 업데이트"""
        return self.vector_store.update_chunk(chunk_id, content)

    def delete_chunk(self, chunk_id: str) -> bool:
        """청크 삭제"""
        return self.vector_store.delete_chunk(chunk_id)

    def ask(self, question: str, category: Optional[str] = None) -> Dict[str, Any]:
        """
        질문에 대한 답변 생성
        Args:
            question: 질문 내용
            category: 검색할 카테고리 (선택사항)
        Returns:
            답변과 참조 문서 정보를 포함한 딕셔너리
        """
        # 질문 임베딩 생성
        query_embedding = self._create_embedding(question)

        # 유사한 청크 검색
        similar_chunks = self.vector_store.search_similar(query_embedding)

        if not similar_chunks:
            return {
                "answer": "죄송합니다. 관련된 정보를 찾을 수 없습니다.",
                "documents": [],
            }

        # 컨텍스트 구성
        context = "\n\n".join([chunk["content"] for chunk in similar_chunks])

        # Gemini를 사용하여 답변 생성
        answer = self._create_chat_completion(
            "주어진 컨텍스트를 기반으로 질문에 답변해주세요. 컨텍스트에 없는 내용은 답변하지 마세요.",
            f"컨텍스트:\n{context}\n\n질문: {question}",
        )

        # 참조 문서 정보 구성
        references = []
        seen_docs = set()  # 중복 문서 제거를 위한 세트
        
        for chunk in similar_chunks:
            doc = self.get_document(chunk["document_id"])
            if doc and doc["id"] not in seen_docs:
                seen_docs.add(doc["id"])
                # 섹션 제목 추출 (있는 경우)
                section_title = ""
                content = chunk["content"]
                if "\n" in content:
                    first_line = content.split("\n")[0]
                    if any(re.match(pattern, first_line) for pattern in [
                        r'^#{1,6}\s+(.+)$',  # Markdown 헤더
                        r'^([A-Z][^.!?]*):$',  # 콜론으로 끝나는 대문자 시작 텍스트
                        r'^\d+\.\s+([^.!?]+)$',  # 숫자로 시작하는 목록
                    ]):
                        section_title = first_line
                
                references.append({
                    "title": doc["title"],
                    "category": doc["category"],
                    "section": section_title if section_title else "문서 본문",
                    "similarity": f"{chunk['similarity']:.2%}",  # 유사도를 퍼센트로 표시
                    "preview": (
                        content[:100] + "..."  # 미리보기는 100자로 제한
                        if len(content) > 100
                        else content
                    ),
                })

        # 유사도 순으로 정렬
        references.sort(key=lambda x: float(x["similarity"].rstrip("%")), reverse=True)

        return {
            "answer": answer,
            "documents": references[:3]  # 상위 3개 문서만 표시
        }

    def _create_embedding(self, text: str) -> List[float]:
        """
        텍스트의 임베딩 벡터 생성
        """
        response = self.client.embeddings.create(model=self.model_name, input=text)
        return response.data[0].embedding

    def _create_chat_completion(self, system_prompt: str, user_prompt: str) -> str:
        """
        Gemini를 사용하여 답변 생성
        """
        # 새로운 채팅 세션 시작
        self.chat_session = self.gemini_model.start_chat(
            history=[
                {
                    "role": "user",
                    "parts": ["당신은 문서 기반 질의응답 시스템입니다. " + system_prompt],
                },
                {
                    "role": "model",
                    "parts": ["네, 이해했습니다. 주어진 컨텍스트를 기반으로 정확하게 답변하도록 하겠습니다."],
                },
            ]
        )
        
        # 질문 전송 및 답변 받기
        response = self.chat_session.send_message(user_prompt)
        return response.text
