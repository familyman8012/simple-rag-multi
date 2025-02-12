import os
from typing import List, Dict, Any
from PyPDF2 import PdfReader
from docx import Document
import re

class DocumentLoader:
    def __init__(self, chunk_size: int = 1500, chunk_overlap: int = 200):
        """
        문서 로더 초기화
        Args:
            chunk_size: 청크 크기 (문자 수, 기본값 1500자)
            chunk_overlap: 청크 간 중복 크기 (문자 수, 기본값 200자)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def process_document(self, file_path: str, category: str = 'general') -> List[Dict[str, Any]]:
        """
        문서를 처리하여 청크로 분할
        Args:
            file_path: 문서 파일 경로
            category: 문서 카테고리
        Returns:
            청크 리스트 (각 청크는 텍스트와 메타데이터를 포함)
        """
        # 파일 확장자 확인
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        # 파일 타입에 따라 텍스트 추출
        if ext == '.pdf':
            text = self._read_pdf(file_path)
        elif ext == '.docx':
            text = self._read_docx(file_path)
        elif ext == '.txt':
            text = self._read_txt(file_path)
        else:
            raise ValueError(f"지원하지 않는 파일 형식입니다: {ext}")

        # 메타데이터 준비
        base_metadata = {
            'source': os.path.basename(file_path),
            'category': category,
            'file_type': ext[1:],  # 앞의 '.' 제거
            'created_at': os.path.getctime(file_path),
            'modified_at': os.path.getmtime(file_path)
        }

        # 텍스트를 청크로 분할
        chunks = self._split_text(text)
        
        # 청크에 메타데이터 추가
        result = []
        for i, chunk in enumerate(chunks):
            metadata = base_metadata.copy()
            metadata.update({
                'chunk_index': i,
                'total_chunks': len(chunks)
            })
            
            result.append({
                'content': chunk,
                'metadata': metadata
            })

        return result

    def _read_pdf(self, file_path: str) -> str:
        """PDF 파일에서 텍스트 추출"""
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text

    def _read_docx(self, file_path: str) -> str:
        """DOCX 파일에서 텍스트 추출"""
        doc = Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text

    def _read_txt(self, file_path: str) -> str:
        """TXT 파일에서 텍스트 추출"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    def _split_text(self, text: str) -> List[str]:
        """
        텍스트를 청크로 분할
        Args:
            text: 분할할 텍스트
        Returns:
            청크 리스트
        """
        # 줄바꿈과 문장 부호를 기준으로 분할
        text = re.sub(r'\n\s*\n', '\n', text)  # 빈 줄 제거
        sentences = []
        
        # 문단 단위로 먼저 분할
        paragraphs = text.split('\n')
        for paragraph in paragraphs:
            # 문장 단위로 분할
            para_sentences = re.split(r'(?<=[.!?])\s*(?=[A-Z가-힣])', paragraph.strip())
            sentences.extend([s.strip() for s in para_sentences if s.strip()])
        
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            # 문장이 너무 길면 단어 단위로 추가 분할
            if len(sentence) > self.chunk_size:
                words = sentence.split()
                temp_sentence = ""
                for word in words:
                    if len(temp_sentence) + len(word) + 1 <= self.chunk_size:
                        temp_sentence += word + " "
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = temp_sentence.strip()
                        temp_sentence = word + " "
                sentence = temp_sentence
            
            # 현재 청크에 문장을 추가할 수 있는지 확인
            if len(current_chunk) + len(sentence) + 1 <= self.chunk_size:
                current_chunk += sentence + " "
            else:
                # 현재 청크가 있으면 저장
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + " "
        
        # 마지막 청크 처리
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # 청크 간 중복 처리
        if self.chunk_overlap > 0 and len(chunks) > 1:
            overlapped_chunks = []
            for i in range(len(chunks)):
                if i == 0:
                    overlapped_chunks.append(chunks[i])
                else:
                    # 이전 청크의 끝부분을 현재 청크의 시작 부분에 추가
                    prev_chunk = chunks[i-1]
                    current_chunk = chunks[i]
                    
                    # 문장 단위로 중복되도록 조정
                    overlap_sentences = re.split(r'(?<=[.!?])\s*(?=[A-Z가-힣])', prev_chunk[-self.chunk_overlap:])
                    if overlap_sentences:
                        overlap_text = overlap_sentences[-1]
                        if len(overlap_text) + len(current_chunk) <= self.chunk_size:
                            overlapped_chunks.append(overlap_text + " " + current_chunk)
                        else:
                            overlapped_chunks.append(current_chunk)
                    else:
                        overlapped_chunks.append(current_chunk)
            
            chunks = overlapped_chunks
        
        return chunks