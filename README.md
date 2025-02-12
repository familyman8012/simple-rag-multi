# RAG (Retrieval-Augmented Generation) 시스템 구현 가이드

## 1. 프로젝트 설정

### 1.1 환경 설정
```bash
# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate  # Windows

# 필요한 패키지 설치
pip install streamlit openai supabase python-dotenv PyPDF2 python-docx
```

### 1.2 환경 변수 설정
`.env` 파일 생성:
```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
OPENAI_API_KEY=your_openai_api_key
```

## 2. Supabase 설정

### 2.1 벡터 저장소 설정
#### 2.1.1 Supabase 프로젝트 생성
1. Supabase 계정 생성
https://supabase.com 접속

"Start your project" 클릭

2. GitHub 계정으로 로그인하거나 이메일로 새 계정 생성

3. 새 프로젝트 생성
로그인 후 "New Project" 버튼 클릭

4. 프로젝트 설정:
Organization: 기본값 사용 또는 새로 생성
Name: "rag-project" (원하는 이름으로 설정)
Database Password: 안전한 비밀번호 설정 (꼭 저장해두세요!)
Region: Seoul (Asia Pacific) 선택 (가장 가까운 리전)
Pricing Plan: Free tier 선택
"Create new project" 클릭하고 생성 완료까지 대기 (약 1-2분 소요)

5. API 키 및 프로젝트 URL 획득
생성된 프로젝트의 대시보드에서 좌측 사이드바의 "Settings" → "API" 메뉴 클릭

6. 다음 정보를 찾아 저장:
Project URL (SUPABASE_URL)
anon/public key (SUPABASE_KEY)
이 정보들은 나중에 .env 파일에 사용됩니다

7. pgvector extension 활성화

8. 좌측 사이드바에서 "SQL Editor" 클릭
새 쿼리 생성 (+ 버튼)

8. documents 테이블 생성:
```sql
-- Enable the pgvector extension
create extension vector;

-- Create a table to store your documents
create table documents (
  id bigserial primary key,
  content text,
  metadata jsonb,
  embedding vector(1536)
);

-- Create a function to search for similar documents
create or replace function match_documents (
  query_embedding vector(1536),
  match_count int
)
returns table (
  id bigint,
  content text,
  metadata jsonb,
  similarity float
)
language plpgsql
as $$
begin
  return query
  select
    documents.id,
    documents.content,
    documents.metadata,
    1 - (documents.embedding <=> query_embedding) as similarity
  from documents
  order by documents.embedding <=> query_embedding
  limit match_count;
end;
$$;
```


## 3. 프로젝트 구조
```
rag-project/
├── src/
│   ├── __init__.py
│   ├── app.py           # Streamlit UI
│   ├── db.py           # Supabase 연동
│   ├── DocumentLoader.py # 문서 처리
│   └── qa.py           # QA 시스템
├── .env
└── README.md
```

## 4. 주요 구현 포인트

### 4.1 문서 처리 (DocumentLoader.py)
- 청크 크기: 300자
- 청크 중복: 50자
- 지원 형식: PDF, TXT, DOCX
- 텍스트 전처리 및 정제

### 4.2 벡터 저장소 (db.py)
- Supabase 연동
- 임베딩 저장 및 검색
- 유사도 검색 기능

### 4.3 QA 시스템 (qa.py)
- OpenAI 임베딩 모델: text-embedding-ada-002
- 채팅 모델: gpt-4o
- 유사도 임계값: 0.1
- 검색 문서 수: 6개

### 4.4 웹 인터페이스 (app.py)
- 파일 업로드 기능
- 문서 처리 상태 관리
- 질문-답변 인터페이스

## 5. 최적화 팁
1. 문서 청크 크기 조정
   - 너무 크면: 관련 없는 내용이 포함될 수 있음
   - 너무 작으면: 문맥이 손실될 수 있음

2. 유사도 검색 최적화
   - 임계값 조정으로 관련성 제어
   - 검색 문서 수 조정으로 컨텍스트 양 제어

3. 상태 관리
   - 세션 상태로 문서 처리 상태 유지
   - 파일 변경 시 자동 초기화

## 6. 디버깅 및 모니터링
- 문서 처리 로그
- 임베딩 저장 확인
- 유사도 검색 결과 확인
- 응답 생성 과정 추적

## 7. 보안 고려사항
- API 키 보안
- 환경 변수 관리
- 사용자 입력 검증
- 파일 업로드 제한
