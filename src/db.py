import os
from typing import List, Dict, Any
from supabase import create_client, Client
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

class VectorStore:
    def __init__(self):
        """
        Supabase 클라이언트 초기화
        """
        url: str = os.getenv("SUPABASE_URL")
        key: str = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise ValueError("SUPABASE_URL과 SUPABASE_KEY가 필요합니다.")
        
        self.supabase: Client = create_client(url, key)

    def add_embeddings(self, texts: List[str], embeddings: List[List[float]], metadatas: List[Dict[str, Any]]) -> None:
        """
        텍스트, 임베딩, 메타데이터를 Supabase에 저장
        """
        print(f"저장할 문서 수: {len(texts)}")  # 디버깅
        for text, embedding, metadata in zip(texts, embeddings, metadatas):
            print(f"문서 내용 (처음 100자): {text[:100]}")  # 디버깅
            try:
                result = self.supabase.table("documents").insert({
                    "content": text,
                    "embedding": embedding,
                    "metadata": metadata
                }).execute()
                print(f"문서 저장 성공: {result.data}")  # 디버깅
            except Exception as e:
                print(f"문서 저장 실패: {str(e)}")  # 디버깅
                raise

    def similarity_search(self, query_embedding: List[float], k: int = 4) -> List[Dict[str, Any]]:
        """
        쿼리 임베딩과 가장 유사한 문서 검색
        """
        print(f"유사도 검색 시작 (k={k})")  # 디버깅
        try:
            # 유사도 검색 쿼리 실행
            response = self.supabase.rpc(
                "match_documents",
                {
                    "query_embedding": query_embedding,
                    "match_count": k
                }
            ).execute()
            
            print(f"검색된 문서 수: {len(response.data) if hasattr(response, 'data') else 0}")  # 디버깅
            if hasattr(response, 'data'):
                for doc in response.data:
                    print(f"문서 유사도: {doc.get('similarity', 0):.3f}")  # 디버깅
                    print(f"문서 내용 (처음 100자): {doc.get('content', '')[:100]}")  # 디버깅
            
            return response.data if hasattr(response, 'data') else []
        except Exception as e:
            print(f"검색 중 오류 발생: {str(e)}")  # 디버깅
            raise

    def delete_all(self) -> None:
        """
        모든 문서 삭제 (테스트용)
        """
        try:
            result = self.supabase.table("documents").delete().neq("id", 0).execute()
            print(f"모든 문서 삭제 완료: {result.data}")  # 디버깅
        except Exception as e:
            print(f"문서 삭제 중 오류 발생: {str(e)}")  # 디버깅
            raise