from typing import List, Dict, Any
import PyPDF2
from pathlib import Path
import docx
import mimetypes
import re

class DocumentLoader:
    def __init__(self, chunk_size: int = 300, chunk_overlap: int = 50):
        """
        문서 로더 초기화
        Args:
            chunk_size: 각 청크의 최대 문자 수 (300자로 줄임)
            chunk_overlap: 청크 간 중복되는 문자 수 (50자로 줄임)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def clean_text(self, text: str) -> str:
        """
        텍스트 전처리
        - 불필요한 공백 제거
        - 개행 문자 정리
        - 특수 문자 처리
        """
        # 여러 개행 문자를 하나로
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # 불필요한 공백 제거
        text = re.sub(r'\s+', ' ', text)
        
        # 문장 끝에 개행 문자 추가
        text = re.sub(r'([.!?])\s', r'\1\n', text)
        
        return text.strip()

    def load_document(self, file_path: str) -> str:
        """
        문서 파일을 읽어서 텍스트로 변환
        지원 형식: PDF, TXT, DOCX
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # 파일 형식 확인
        mime_type, _ = mimetypes.guess_type(str(file_path))
        
        if mime_type == 'application/pdf':
            text = self._load_pdf(file_path)
        elif mime_type == 'text/plain':
            text = self._load_txt(file_path)
        elif mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            text = self._load_docx(file_path)
        else:
            raise ValueError(f"Unsupported file type: {mime_type}")
        
        # 텍스트 전처리
        return self.clean_text(text)

    def _load_pdf(self, file_path: Path) -> str:
        """PDF 파일 읽기"""
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text

    def _load_txt(self, file_path: Path) -> str:
        """TXT 파일 읽기"""
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()

    def _load_docx(self, file_path: Path) -> str:
        """DOCX 파일 읽기"""
        doc = docx.Document(file_path)
        return "\n".join([paragraph.text for paragraph in doc.paragraphs])

    def split_text(self, text: str) -> List[Dict[str, Any]]:
        """
        텍스트를 청크로 분할
        - 문장 단위로 분할
        - 청크 크기 조정
        - 중복 영역 포함
        """
        chunks = []
        sentences = text.split('\n')
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            sentence_size = len(sentence)
            
            # 현재 청크가 비어있고, 문장이 청크 크기보다 큰 경우
            if not current_chunk and sentence_size > self.chunk_size:
                # 문장을 더 작은 단위로 분할
                words = sentence.split()
                temp_chunk = []
                temp_size = 0
                
                for word in words:
                    word_size = len(word) + 1  # 공백 포함
                    if temp_size + word_size > self.chunk_size:
                        if temp_chunk:
                            chunks.append({
                                "content": " ".join(temp_chunk),
                                "metadata": {
                                    "source": "large_sentence_split",
                                    "size": temp_size
                                }
                            })
                        temp_chunk = [word]
                        temp_size = word_size
                    else:
                        temp_chunk.append(word)
                        temp_size += word_size
                
                if temp_chunk:
                    chunks.append({
                        "content": " ".join(temp_chunk),
                        "metadata": {
                            "source": "large_sentence_split",
                            "size": temp_size
                        }
                    })
                continue
            
            # 일반적인 경우
            if current_size + sentence_size <= self.chunk_size:
                current_chunk.append(sentence)
                current_size += sentence_size
            else:
                if current_chunk:
                    chunks.append({
                        "content": "\n".join(current_chunk),
                        "metadata": {
                            "source": "normal_split",
                            "size": current_size
                        }
                    })
                current_chunk = [sentence]
                current_size = sentence_size
        
        # 마지막 청크 처리
        if current_chunk:
            chunks.append({
                "content": "\n".join(current_chunk),
                "metadata": {
                    "source": "normal_split",
                    "size": current_size
                }
            })
        
        return chunks

    def process_document(self, file_path: str) -> List[Dict[str, Any]]:
        """
        문서 파일을 처리하여 청크로 분할
        """
        # 문서 읽기
        text = self.load_document(file_path)
        
        # 텍스트 분할
        chunks = self.split_text(text)
        
        return chunks