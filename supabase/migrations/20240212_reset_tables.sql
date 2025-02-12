-- 기존 테이블과 함수 삭제
drop table if exists documents cascade;
drop table if exists chunks cascade;
drop function if exists match_documents;
drop function if exists match_chunks;

-- 문서 테이블 생성
create table if not exists documents (
    id bigint primary key generated always as identity,
    title text not null,
    category text not null default 'general',
    file_name text,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    total_chunks integer not null
);

-- 청크 테이블 생성 (벡터 저장소)
create table if not exists chunks (
    id bigint primary key generated always as identity,
    document_id bigint references documents(id) on delete cascade,
    content text not null,
    embedding vector(1536),
    chunk_index integer not null,
    metadata jsonb,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 벡터 검색을 위한 함수 생성
create or replace function match_chunks(
    query_embedding vector(1536),
    match_count int default 5
)
returns table (
    id bigint,
    content text,
    document_id bigint,
    chunk_index integer,
    similarity float
)
language plpgsql
as $$
begin
    return query
    select
        chunks.id,
        chunks.content,
        chunks.document_id,
        chunks.chunk_index,
        1 - (chunks.embedding <=> query_embedding) as similarity
    from chunks
    where chunks.embedding is not null
    order by chunks.embedding <=> query_embedding
    limit match_count;
end;
$$;
