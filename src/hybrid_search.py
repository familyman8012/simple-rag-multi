from typing import List, Dict, Any
from rank_bm25 import BM25Okapi
import numpy as np

class HybridSearch:
    def __init__(self, alpha: float = 0.3):
        """
        하이브리드 검색 초기화
        Args:
            alpha: BM25와 벡터 검색 결과를 결합할 때 BM25의 가중치 (0~1)
        """
        self.documents: List[str] = []
        self.embeddings: List[List[float]] = []
        self.metadata: List[Dict[str, Any]] = []
        self.bm25: BM25Okapi = None
        self.alpha = alpha

    def add_documents(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadata: List[Dict[str, Any]] = None
    ) -> None:
        """
        문서 추가
        """
        self.documents = texts
        self.embeddings = embeddings
        self.metadata = metadata if metadata else [{} for _ in texts]
        
        # BM25 초기화
        tokenized_docs = [doc.split() for doc in texts]
        self.bm25 = BM25Okapi(tokenized_docs)

    def search(
        self,
        query: str,
        query_embedding: List[float],
        filter: Dict[str, Any] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        하이브리드 검색 수행
        Args:
            query: 검색 쿼리
            query_embedding: 쿼리 임베딩
            filter: 메타데이터 필터 (예: {'metadata.category': 'dating'})
            top_k: 반환할 최대 문서 수
        """
        if not self.documents:
            return []

        # 필터 적용을 위한 문서 인덱스 찾기
        valid_indices = []
        if filter:
            for i, meta in enumerate(self.metadata):
                is_valid = True
                for key, value in filter.items():
                    # metadata.category -> metadata['category']
                    key_parts = key.split('.')
                    current = meta
                    for part in key_parts[1:]:  # metadata. 제외
                        if isinstance(current, dict) and part in current:
                            current = current[part]
                        else:
                            is_valid = False
                            break
                    
                    if isinstance(value, dict):  # $in 같은 연산자 처리
                        if '$in' in value and current not in value['$in']:
                            is_valid = False
                    elif current != value:
                        is_valid = False
                
                if is_valid:
                    valid_indices.append(i)
        else:
            valid_indices = list(range(len(self.documents)))

        if not valid_indices:
            return []

        # 필터링된 문서들만 사용
        filtered_docs = [self.documents[i] for i in valid_indices]
        filtered_embeddings = [self.embeddings[i] for i in valid_indices]
        
        # BM25 점수 계산
        tokenized_query = query.split()
        bm25_scores = self.bm25.get_scores(tokenized_query)
        bm25_scores = [bm25_scores[i] for i in valid_indices]
        
        # 벡터 유사도 계산 (코사인 유사도)
        vector_scores = []
        query_embedding = np.array(query_embedding)
        for doc_embedding in filtered_embeddings:
            similarity = np.dot(query_embedding, doc_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(doc_embedding)
            )
            vector_scores.append(similarity)
        
        # 점수 정규화
        if bm25_scores:
            bm25_scores = np.array(bm25_scores)
            bm25_scores = (bm25_scores - bm25_scores.min()) / (bm25_scores.max() - bm25_scores.min() + 1e-6)
        
        if vector_scores:
            vector_scores = np.array(vector_scores)
            vector_scores = (vector_scores - vector_scores.min()) / (vector_scores.max() - vector_scores.min() + 1e-6)
        
        # 최종 점수 계산
        final_scores = self.alpha * bm25_scores + (1 - self.alpha) * vector_scores
        
        # 상위 k개 결과 반환
        top_indices = np.argsort(final_scores)[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
            original_idx = valid_indices[idx]
            results.append({
                'content': self.documents[original_idx],
                'metadata': self.metadata[original_idx],
                'similarity': float(final_scores[idx])
            })
        
        return results
