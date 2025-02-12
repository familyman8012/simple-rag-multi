import os
from typing import List, Dict, Any, Optional
from supabase import create_client, Client
import numpy as np
from datetime import datetime

class VectorStore:
    def __init__(self):
        url: str = os.environ.get("SUPABASE_URL")
        key: str = os.environ.get("SUPABASE_KEY")
        
        if not url or not key:
            raise ValueError("SUPABASE_URL과 SUPABASE_KEY가 환경변수에 설정되어 있어야 합니다.")
        
        self.supabase: Client = create_client(url, key)
        self._init_tables()
    
    def _init_tables(self):
        """필요한 테이블 초기화"""
        # documents 테이블 생성
        self.supabase.table("documents").select("*").limit(1).execute()
        # chunks 테이블 생성 (기존 vector_store)
        self.supabase.table("chunks").select("*").limit(1).execute()
    
    def add_document(self, chunks: List[Dict[str, Any]], metadata: Dict[str, Any]) -> int:
        """
        새 문서와 관련 청크들을 추가
        Args:
            chunks: 문서의 청크 리스트
            metadata: 문서 메타데이터
        Returns:
            생성된 문서 ID
        """
        # 문서 메타데이터 저장
        doc_data = {
            "title": metadata.get("title", "제목 없음"),
            "category": metadata.get("category", "general"),
            "file_name": metadata.get("original_filename", ""),
            "created_at": datetime.now().isoformat(),
            "total_chunks": len(chunks)
        }
        
        response = self.supabase.table("documents").insert(doc_data).execute()
        doc_id = response.data[0]['id']
        
        # 청크 데이터 저장
        for i, chunk in enumerate(chunks):
            chunk_data = {
                "document_id": doc_id,
                "content": chunk["content"],
                "embedding": chunk["embedding"],
                "chunk_index": i,
                "metadata": {
                    **metadata,
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                }
            }
            self.supabase.table("chunks").insert(chunk_data).execute()
        
        return doc_id
    
    def get_document(self, doc_id: int) -> Optional[Dict[str, Any]]:
        """문서 정보 조회"""
        response = self.supabase.table("documents").select("*").eq("id", doc_id).execute()
        if not response.data:
            return None
        return response.data[0]
    
    def list_documents(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """문서 목록 조회"""
        query = self.supabase.table("documents").select("*").order("created_at", desc=True)
        if category:
            query = query.eq("category", category)
        response = query.execute()
        return response.data
    
    def update_document(self, doc_id: int, updates: Dict[str, Any]) -> bool:
        """문서 정보 업데이트"""
        try:
            self.supabase.table("documents").update(updates).eq("id", doc_id).execute()
            return True
        except Exception:
            return False
    
    def delete_document(self, doc_id: int) -> bool:
        """문서와 관련 청크 모두 삭제"""
        try:
            # 관련 청크는 cascade로 자동 삭제됨
            self.supabase.table("documents").delete().eq("id", doc_id).execute()
            return True
        except Exception:
            return False
    
    def list_document_chunks(self, doc_id: int) -> List[Dict[str, Any]]:
        """특정 문서의 청크 목록 조회"""
        response = self.supabase.table("chunks").select("*").eq("document_id", doc_id).order("chunk_index").execute()
        return response.data
    
    def update_chunk(self, chunk_id: int, content: str) -> bool:
        """청크 내용 업데이트"""
        try:
            self.supabase.table("chunks").update({"content": content}).eq("id", chunk_id).execute()
            return True
        except Exception:
            return False
    
    def delete_chunk(self, chunk_id: int) -> bool:
        """청크 삭제"""
        try:
            self.supabase.table("chunks").delete().eq("id", chunk_id).execute()
            return True
        except Exception:
            return False
    
    def search_similar(self, query_embedding: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        """유사한 청크 검색"""
        response = self.supabase.rpc(
            'match_chunks',
            {
                'query_embedding': query_embedding,
                'match_count': limit
            }
        ).execute()
        
        return response.data