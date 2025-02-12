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

    def _extract_sections(self, text: str) -> List[Dict[str, Any]]:
        """
        텍스트에서 섹션을 추출
        Args:
            text: 원본 텍스트
        Returns:
            섹션 리스트 (각 섹션은 제목과 내용을 포함)
        """
        # 일반적인 섹션 헤더 패턴
        section_patterns = [
            r'^#{1,6}\s+(.+)$',  # Markdown 헤더
            r'^([A-Z][^.!?]*):$',  # 콜론으로 끝나는 대문자 시작 텍스트
            r'^\d+\.\s+([^.!?]+)$',  # 숫자로 시작하는 목록
            r'^[A-Z][^.!?]*\n[-=]+$',  # 밑줄로 강조된 텍스트
        ]
        
        lines = text.split('\n')
        sections = []
        current_section = {'title': '', 'content': []}
        
        for line in lines:
            is_header = False
            for pattern in section_patterns:
                if re.match(pattern, line):
                    if current_section['content']:
                        sections.append(current_section)
                        current_section = {'title': '', 'content': []}
                    current_section['title'] = line
                    is_header = True
                    break
            
            if not is_header:
                current_section['content'].append(line)
        
        if current_section['content']:
            sections.append(current_section)
        
        return sections

    def _split_into_sentences(self, text: str) -> List[str]:
        """
        텍스트를 문장 단위로 분할
        Args:
            text: 분할할 텍스트
        Returns:
            문장 리스트
        """
        # 문장 종료 패턴
        sentence_endings = r'[.!?][\'")\]]* *'
        
        # 약어와 특수 케이스 처리
        abbreviations = r'(?<!Mr)(?<!Mrs)(?<!Dr)(?<!Prof)(?<!Sr)(?<!Jr)'
        
        # 문장 분할
        pattern = f'{abbreviations}{sentence_endings}'
        sentences = re.split(pattern, text)
        
        # 빈 문장 제거 및 정리
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences

    def _split_text(self, text: str) -> List[str]:
        """
        텍스트를 의미 기반으로 청크 분할
        Args:
            text: 분할할 텍스트
        Returns:
            청크 리스트
        """
        # 1. 섹션 추출
        sections = self._extract_sections(text)
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for section in sections:
            # 섹션 제목 처리
            if section['title']:
                if current_chunk and current_length > 0:
                    chunks.append('\n'.join(current_chunk))
                    current_chunk = []
                    current_length = 0
                current_chunk.append(section['title'])
                current_length += len(section['title'])
            
            # 섹션 내용을 문장 단위로 분할
            content_text = '\n'.join(section['content'])
            sentences = self._split_into_sentences(content_text)
            
            for sentence in sentences:
                # 현재 청크가 너무 커지면 새 청크 시작
                if current_length + len(sentence) > self.chunk_size:
                    if current_chunk:
                        chunks.append('\n'.join(current_chunk))
                        # 중복을 위해 마지막 일부 문장 유지
                        overlap_size = 0
                        overlap_chunk = []
                        for s in reversed(current_chunk):
                            if overlap_size + len(s) <= self.chunk_overlap:
                                overlap_chunk.insert(0, s)
                                overlap_size += len(s)
                            else:
                                break
                        current_chunk = overlap_chunk
                        current_length = sum(len(s) for s in current_chunk)
                
                current_chunk.append(sentence)
                current_length += len(sentence)
        
        # 마지막 청크 처리
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        return chunks