# RAG (Retrieval-Augmented Generation) 시스템 구현 순서

## 1. 초기 설정 및 API 키 획득
### 1.1 Supabase 설정
- Supabase 계정 생성
- 새 프로젝트 생성
- API 키 및 프로젝트 URL 획득
- pgvector extension 활성화


Supabase 계정 생성
https://supabase.com 접속
"Start your project" 클릭
GitHub 계정으로 로그인하거나 이메일로 새 계정 생성
새 프로젝트 생성
로그인 후 "New Project" 버튼 클릭
프로젝트 설정:
Organization: 기본값 사용 또는 새로 생성
Name: "rag-project" (원하는 이름으로 설정)
Database Password: 안전한 비밀번호 설정 (꼭 저장해두세요!)
Region: Seoul (Asia Pacific) 선택 (가장 가까운 리전)
Pricing Plan: Free tier 선택
"Create new project" 클릭하고 생성 완료까지 대기 (약 1-2분 소요)
API 키 및 프로젝트 URL 획득
생성된 프로젝트의 대시보드에서 좌측 사이드바의 "Settings" → "API" 메뉴 클릭
다음 정보를 찾아 저장:
Project URL (SUPABASE_URL)
anon/public key (SUPABASE_KEY)
이 정보들은 나중에 .env 파일에 사용됩니다
pgvector extension 활성화
좌측 사이드바에서 "SQL Editor" 클릭
새 쿼리 생성 (+ 버튼)
다음 SQL 명령어 실행:
sql
CopyInsert
-- vector extension 활성화
create extension vector;

-- 벡터를 저장할 테이블 생성
create table documents (
  id bigserial primary key,
  content text,
  metadata jsonb,
  embedding vector(1536)
);

-- 벡터 검색을 위한 인덱스 생성
create index on documents 
using ivfflat (embedding vector_cosine_ops)
with (lists = 100);



DROP FUNCTION IF EXISTS match_documents;

CREATE OR REPLACE FUNCTION match_documents (
    query_embedding vector(1536),
    match_count int
)
RETURNS TABLE (
    id bigint,
    content text,
    metadata jsonb,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        documents.id,
        documents.content,
        documents.metadata,
        1 - (documents.embedding <=> query_embedding) as similarity
    FROM documents
    ORDER BY documents.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;



### 1.2 OpenAI 설정
- OpenAI 계정 생성
- API 키 발급

### 1.3 로컬 프로젝트 설정
- 프로젝트 디렉토리 생성
- 가상환경 설정
- .env 파일 생성 및 API 키 저장
- requirements.txt 생성 및 기본 패키지 설치
  ```
  python-dotenv
  openai
  supabase
  PyPDF2
  streamlit
  ```

## 2. 기본 기능 구현
### 2.1 PDF 처리 기능
- PyPDF2를 사용한 기본 PDF 텍스트 추출
- 텍스트 청크 분할 구현

### 2.2 Supabase Vector Store 구현
- Supabase 연결 설정
- 벡터 저장을 위한 테이블 생성
- 벡터 저장 및 검색 함수 구현

### 2.3 OpenAI 연동
- 텍스트 임베딩 생성 함수
- GPT 응답 생성 함수

### 2.4 Streamlit UI 구현
- 파일 업로드 인터페이스
- 채팅 인터페이스
- 전체 기능 통합

## 3. 테스트 및 개선
- 기본 기능 테스트
- 에러 처리 추가
- 성능 개선

## 4. 향후 개선사항 (필요시)
- PDF 처리 개선 (OCR 등)
- 응답 품질 향상
- UI/UX 개선
- 성능 최적화

## 상세 구현 가이드

### 1. 초기 설정 및 API 키 획득

#### Supabase 설정 방법
1. https://supabase.com 접속
2. 새 프로젝트 생성
3. SQL 에디터에서 pgvector extension 활성화:
   ```sql
   create extension vector;
   ```
4. 프로젝트 설정에서 API 키와 URL 복사

#### OpenAI 설정 방법
1. https://platform.openai.com 접속
2. API 키 생성
3. 사용량 및 결제 설정

#### 로컬 프로젝트 초기화
```bash
# 프로젝트 디렉토리 생성
mkdir rag-project
cd rag-project

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate  # Windows

# 기본 패키지 설치
pip install python-dotenv openai supabase PyPDF2 streamlit

# .env 파일 생성
touch .env
```

.env 파일 구성:
```
OPENAI_API_KEY=your_openai_api_key
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_api_key
```


db.py 파일에 구현된 주요 기능들은 다음과 같습니다:

VectorStore 클래스:
add_embeddings(): 텍스트, 임베딩, 메타데이터를 Supabase에 저장
similarity_search(): 쿼리 임베딩과 가장 유사한 문서 검색
delete_all(): 모든 문서 삭제 (테스트용)


pdf_loader.py 파일에 구현된 주요 기능들은 다음과 같습니다:

PDFLoader 클래스:
load_pdf(): PDF 파일을 읽어서 텍스트로 변환
split_text(): 긴 텍스트를 적절한 크기의 청크로 분할
process_pdf(): PDF 파일을 처리하여 청크로 분할



qa.py 파일에 구현된 주요 기능들은 다음과 같습니다:

QASystem 클래스:
create_embeddings(): OpenAI API를 사용하여 텍스트의 임베딩 생성
add_documents(): 문서 청크들을 벡터 스토어에 추가
generate_answer(): 컨텍스트를 바탕으로 질문에 대한 답변 생성
answer_question(): 전체 QA 프로세스 처리 (임베딩 생성 → 유사 문서 검색 → 답변 생성)
주요 특징:

text-embedding-ada-002 모델로 임베딩 생성
gpt-4o 모델로 답변 생성
시스템 프롬프트를 통해 컨텍스트 기반 답변 유도
관련성 높은 상위 4개 문서를 기반으로 답변 생성



app.py를 구현하여 Streamlit UI