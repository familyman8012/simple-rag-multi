import hashlib
import json
import os
from pathlib import Path
from typing import List, Dict, Optional

class EmbeddingCache:
    def __init__(self, cache_dir: str = ".cache/embeddings"):
        """
        임베딩 캐시 초기화
        Args:
            cache_dir: 캐시 파일을 저장할 디렉토리
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def _get_cache_key(self, text: str, model_name: str) -> str:
        """
        텍스트와 모델명으로부터 캐시 키 생성
        """
        # 텍스트와 모델명을 합쳐서 해시 생성
        content = f"{text}:{model_name}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """
        캐시 키에 해당하는 파일 경로 반환
        """
        return self.cache_dir / f"{cache_key}.json"
    
    def get(self, text: str, model_name: str) -> Optional[List[float]]:
        """
        캐시된 임베딩 가져오기
        Returns:
            임베딩 벡터 또는 None (캐시 미스)
        """
        cache_key = self._get_cache_key(text, model_name)
        cache_path = self._get_cache_path(cache_key)
        
        if cache_path.exists():
            try:
                with open(cache_path, 'r') as f:
                    cache_data = json.load(f)
                return cache_data['embedding']
            except (json.JSONDecodeError, KeyError, IOError):
                # 캐시 파일이 손상된 경우 삭제
                cache_path.unlink(missing_ok=True)
                return None
        return None
    
    def set(self, text: str, model_name: str, embedding: List[float]) -> None:
        """
        임베딩을 캐시에 저장
        """
        cache_key = self._get_cache_key(text, model_name)
        cache_path = self._get_cache_path(cache_key)
        
        cache_data = {
            'text': text,
            'model': model_name,
            'embedding': embedding
        }
        
        try:
            with open(cache_path, 'w') as f:
                json.dump(cache_data, f)
        except IOError:
            # 캐시 저장 실패 시 무시하고 계속 진행
            pass
    
    def clear(self) -> None:
        """
        모든 캐시 삭제
        """
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink(missing_ok=True)
            
    def get_size(self) -> int:
        """
        현재 캐시된 임베딩 개수 반환
        """
        return len(list(self.cache_dir.glob("*.json")))
