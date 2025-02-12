from typing import List, Dict, Any
import os
from openai import OpenAI
from dotenv import load_dotenv
from db import VectorStore

# 환경 변수 로드
load_dotenv()

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class QASystem:
    def __init__(self):
        """
        QA 시스템 초기화
        """
        self.vector_store = VectorStore()
        self.embedding_model = "text-embedding-ada-002"
        self.chat_model = "gpt-4o"  # 올바른 모델명으로 수정
        self.similarity_threshold = 0.7  # 임계값을 낮춤

    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        텍스트의 임베딩 생성
        """
        embeddings = []
        for text in texts:
            response = client.embeddings.create(model=self.embedding_model, input=text)
            embeddings.append(response.data[0].embedding)
        return embeddings

    def add_documents(self, chunks: List[Dict[str, Any]]) -> None:
        """
        문서 청크들을 벡터 스토어에 추가
        """
        texts = [chunk["content"] for chunk in chunks]
        embeddings = self.create_embeddings(texts)
        metadatas = [chunk["metadata"] for chunk in chunks]
        self.vector_store.add_embeddings(texts, embeddings, metadatas)

    def generate_answer(
        self, question: str, context: str, relevant_docs: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        컨텍스트를 바탕으로 질문에 답변하고 요약 제공
        """
        # 시스템 프롬프트 개선
        system_prompt = """
        당신은 문서 기반 질의응답 시스템입니다. 주어진 컨텍스트를 바탕으로 다음 작업을 수행해주세요:

        1. 질문에 대한 답변:
        - 컨텍스트의 정보만을 사용하여 답변하세요
        - 확실하지 않은 정보는 "확실하지 않습니다"라고 표현하세요
        - 정보가 없다면 "주어진 문서에서 해당 정보를 찾을 수 없습니다"라고 답변하세요

        2. 관련 문서 요약:
        - 검색된 관련 문서들의 핵심 내용을 간단히 요약해주세요
        - 각 문서의 주요 키워드나 주제를 포함해주세요

        답변 형식:
        답변: [질문에 대한 직접적인 답변]
        요약: [관련 문서들의 핵심 내용 요약]
        """

        # 유사도 점수 포함
        context_with_scores = "\n\n".join(
            [
                f"[유사도: {doc.get('similarity', 0):.2f}]\n{doc['content']}"
                for doc in relevant_docs
            ]
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"컨텍스트:\n{context_with_scores}\n\n질문: {question}",
            },
        ]

        response = client.chat.completions.create(
            model=self.chat_model, messages=messages, temperature=0, max_tokens=800
        )

        return response.choices[0].message.content

    def answer_question(self, question: str, k: int = 6) -> str:
        """
        질문에 대한 답변 생성
        Args:
            question: 질문
            k: 검색할 유사 문서 수 (6개로 증가)
        """
        # 질문 임베딩 생성
        question_embedding = self.create_embeddings([question])[0]

        # 관련 문서 검색 (더 많은 문서 검색)
        relevant_docs = self.vector_store.similarity_search(question_embedding, k=k)

        if not relevant_docs:
            return "관련된 문서를 찾을 수 없습니다."

        # 유사도 임계값을 낮춤
        self.similarity_threshold = 0.1
        filtered_docs = [
            doc
            for doc in relevant_docs
            if doc.get("similarity", 0) > self.similarity_threshold
        ]

        if not filtered_docs:
            return "질문과 충분히 관련된 문서를 찾을 수 없습니다."

        # 컨텍스트 구성 (유사도 순으로 정렬)
        filtered_docs.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        context = "\n\n".join([doc["content"] for doc in filtered_docs])

        # 답변 생성
        return self.generate_answer(question, context, filtered_docs)
