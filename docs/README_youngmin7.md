# youngmin7 데이터베이스 임베딩 & QA 시스템

## 개요
sungjun 인스턴스의 youngmin7 데이터베이스에 저장된 그래프에 임베딩을 추가하고, 이를 기반으로 질의응답하는 시스템입니다.

## 시스템 구성

### 1. `embed_youngmin7.py`
- **기능**: 그래프의 노드와 관계에 임베딩 추가
- **임베딩 모델**: `jhgan/ko-sroberta-multitask` (한국어 최적화)
- **처리 대상**:
  - 모든 노드 (King, Person, Event, Location 등)
  - 모든 관계 (SUCCEEDED_BY, FATHER_OF, PARTICIPATED_IN 등)
- **출력**: 각 노드/관계에 `embedding`, `embedding_text` 속성 추가

### 2. `qa_youngmin7.py`
- **기능**: 임베딩 기반 질의응답 시스템
- **검색 방식**:
  - 벡터 유사도 검색 (노드 + 관계)
  - 그래프 탐색 (연결된 개체 조회)
  - 하이브리드 검색 (벡터 + 그래프)
- **LLM**: Ollama 기반 답변 생성 (exaone3.5:7.8b)

---

## 사용 방법

### 1단계: 환경 설정

#### .env 파일 설정
`.env` 파일에서 다음 설정을 확인/수정하세요:

```env
# Neo4j 설정
NEO4J_URI=bolt://sungjun:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=qqqqqqqq
NEO4J_DATABASE=youngmin7

# Ollama 설정
OLLAMA_MODEL=exaone3.5:7.8b
OLLAMA_BASE_URL=http://localhost:11434
REQUEST_TIMEOUT=900
```

**중요**: 
- `NEO4J_URI`는 sungjun 인스턴스 주소로 설정
- `NEO4J_DATABASE`는 youngmin7로 설정
- Ollama가 실행 중인지 확인 (`ollama serve`)

### 2단계: 임베딩 추가

```bash
python embed_youngmin7.py
```

**실행 과정**:
1. 임베딩 모델 로드 (jhgan/ko-sroberta-multitask)
2. Neo4j 연결 (sungjun:7687/youngmin7)
3. 모든 노드 조회 및 임베딩 생성
4. 모든 관계 조회 및 임베딩 생성
5. 벡터 인덱스 생성
6. 통계 출력

**예상 출력**:
```
================================================================================
🚀 youngmin7 데이터베이스 임베딩 시스템
================================================================================
인스턴스: bolt://sungjun:7687
데이터베이스: youngmin7
사용자: neo4j

📦 임베딩 모델 로드: jhgan/ko-sroberta-multitask
✓ 임베딩 차원: 768

📡 Neo4j 연결 중...
✓ Neo4j 연결 성공

📊 노드 조회 중...
✓ 1,234개 노드 발견

🎯 노드 임베딩 생성 중...
노드 임베딩: 100%|████████████████████| 1234/1234 [00:45<00:00, 27.31it/s]
✓ 노드 임베딩 완료: 1,234개 성공, 0개 실패

🔗 관계 조회 중...
✓ 2,567개 관계 발견

🎯 관계 임베딩 생성 중...
관계 임베딩: 100%|████████████████████| 2567/2567 [01:23<00:00, 30.84it/s]
✓ 관계 임베딩 완료: 2,567개 성공, 0개 실패

🔍 벡터 인덱스 생성 (차원: 768)...
✓ 노드 벡터 인덱스 생성 완료
✓ 관계 벡터 인덱스 생성 완료

================================================================================
📊 임베딩 통계
================================================================================

✓ 노드 임베딩: 1,234개

레이블별 분포:
  - Person: 567개
  - Event: 234개
  - Location: 189개
  ...

✓ 관계 임베딩: 2,567개

임베딩 샘플:

  1. 세종대왕 (King)
     [왕] 세종대왕 - reign_start: 1418, reign_end: 1450. 관계: FATHER_OF 문종, ...

================================================================================
✅ 임베딩 완료!
================================================================================
```

**소요 시간**: 
- 1,000개 노드: 약 40초
- 2,000개 관계: 약 1분 20초
- 총 약 2~3분

### 3단계: 질의응답 실행

```bash
python qa_youngmin7.py
```

**실행 과정**:
1. 임베딩 모델 로드
2. LLM 모델 로드 (Ollama)
3. Neo4j 연결
4. 대화형 모드 시작

**사용 예시**:
```
================================================================================
🤖 youngmin7 질의응답 시스템 초기화
================================================================================
📦 임베딩 모델 로드 중...
✓ 임베딩 모델 로드 완료
📦 LLM 모델 로드 중...
✓ LLM 모델 로드 완료
📡 Neo4j 연결 중...
✓ Neo4j 연결 완료

================================================================================
✅ 초기화 완료! 질문을 입력하세요.
================================================================================

💡 사용 방법:
  - 질문을 입력하세요
  - 'exit' 또는 'quit'를 입력하면 종료됩니다
  - 'clear'를 입력하면 화면을 정리합니다
--------------------------------------------------------------------------------

🤔 질문 > 세종대왕의 아들은 누구인가요?

💬 질문: 세종대왕의 아들은 누구인가요?
--------------------------------------------------------------------------------
🔍 관련 개체 검색 중...
✓ 5개 개체 발견
🔗 관련 관계 검색 중...
✓ 3개 관계 발견
📊 그래프 컨텍스트 조회 중...
🤖 답변 생성 중...

================================================================================
💡 답변:
================================================================================
세종대왕의 아들로는 문종이 있습니다. 지식 그래프 정보에 따르면 세종대왕과 
문종 사이에 FATHER_OF 관계가 존재하며, 문종은 세종의 뒤를 이어 왕위를 
계승했습니다 (SUCCEEDED_BY 관계).
================================================================================

🤔 질문 >
```

---

## 주요 기능

### 임베딩 시스템 (`embed_youngmin7.py`)

#### 노드 임베딩
- **텍스트 구성**:
  ```
  [타입] 이름 - 속성1: 값1, 속성2: 값2
  ```
- **예시**:
  ```
  [왕] 세종대왕 - reign_start: 1418, reign_end: 1450
  [인물] 이순신 - title: 장군, birth_year: 1545
  ```

#### 관계 임베딩
- **텍스트 구성**:
  ```
  출발노드 --[관계타입]--> 도착노드
  ```
- **예시**:
  ```
  세종대왕 --[계승]--> 문종
  이순신 --[참여]--> 임진왜란
  ```

#### 벡터 인덱스
- **노드 인덱스**: `node_embeddings` (차원: 768)
- **관계 인덱스**: `rel_embeddings` (차원: 768)
- **유사도 함수**: 코사인 유사도

### QA 시스템 (`qa_youngmin7.py`)

#### 검색 전략

1. **벡터 검색 (Vector Search)**
   - 질문을 임베딩으로 변환
   - 코사인 유사도로 관련 노드/관계 검색
   - 상위 k개 결과 반환

2. **그래프 탐색 (Graph Traversal)**
   - 최상위 개체를 중심으로 1~2홉 탐색
   - 연결된 개체와 관계 정보 수집

3. **하이브리드 검색**
   - 벡터 검색 + 그래프 탐색 결합
   - 컨텍스트 풍부화

#### 답변 생성

1. **컨텍스트 구성**:
   - 벡터 검색 결과 (노드 top 5)
   - 벡터 검색 결과 (관계 top 3)
   - 그래프 컨텍스트 (연결된 개체)

2. **LLM 프롬프트**:
   ```
   당신은 조선왕조 역사 전문가입니다.
   주어진 지식 그래프 정보를 바탕으로 질문에 답변하세요.
   
   [지식 그래프 정보]
   ...
   
   [질문]
   ...
   
   [답변 규칙]
   1. 그래프 정보만 사용
   2. 간결하고 명확하게 (2-4문장)
   3. 근거 명시
   4. 정보 부족 시 솔직히 답변
   ```

3. **답변 출력**

---

## 코드 구조

### `embed_youngmin7.py`

```python
class GraphEmbedder:
    """임베딩 생성기"""
    def embed_text(text: str) -> list
        # 텍스트를 768차원 벡터로 변환

def create_node_text(node: dict) -> str
    # 노드 정보 → 임베딩용 텍스트

def create_rel_text(rel: dict) -> str
    # 관계 정보 → 임베딩용 텍스트

def get_all_nodes(driver, database) -> list
    # 모든 노드 조회

def get_all_relationships(driver, database) -> list
    # 모든 관계 조회

def update_node_embedding(driver, database, node_id, embedding, text)
    # 노드에 임베딩 저장

def update_rel_embedding(driver, database, rel_id, embedding, text)
    # 관계에 임베딩 저장

def create_vector_indexes(driver, database, dim)
    # 벡터 인덱스 생성

def add_embeddings_to_youngmin7(...)
    # 메인 실행 함수
```

### `qa_youngmin7.py`

```python
class Youngmin7QASystem:
    """QA 시스템"""
    
    def __init__(...)
        # 초기화: 모델 로드, Neo4j 연결
    
    def vector_search_nodes(query_text, top_k) -> list
        # 벡터 검색: 노드
    
    def vector_search_relationships(query_text, top_k) -> list
        # 벡터 검색: 관계
    
    def get_entity_context(entity_name, max_depth) -> dict
        # 그래프 탐색: 개체 주변 컨텍스트
    
    def ask(question, top_k, use_relationships) -> str
        # 질문 → 답변 (전체 파이프라인)
    
    def generate_answer(question, context) -> str
        # LLM으로 답변 생성
    
    def interactive_mode()
        # 대화형 모드
```

---

## 시스템 요구사항

### 하드웨어
- **GPU**: RTX 3050 이상 (4GB VRAM)
- **RAM**: 16GB 이상 (32GB 권장)
- **저장공간**: 10GB 이상

### 소프트웨어
- **Python**: 3.9 이상
- **Neo4j**: 5.13 이상 (벡터 인덱스 지원)
- **Ollama**: 최신 버전

### Python 패키지
```
neo4j>=5.15.0
sentence-transformers>=2.2.0
llama-index>=0.9.0
llama-index-llms-ollama>=0.1.0
python-dotenv>=1.0.0
numpy>=1.24.0
tqdm>=4.65.0
```

설치:
```bash
pip install neo4j sentence-transformers llama-index llama-index-llms-ollama python-dotenv numpy tqdm
```

---

##  문제 해결

### 1. Neo4j 연결 실패
**증상**: `❌ Neo4j 연결 실패: ...`

**해결 방법**:
- Neo4j가 실행 중인지 확인
- `.env` 파일의 URI, 사용자명, 비밀번호 확인
- 방화벽에서 7687 포트 허용
- sungjun 인스턴스 주소 확인

### 2. 벡터 인덱스 생성 실패
**증상**: `⚠️ 노드 인덱스 생성 실패 (Neo4j 5.13+ 필요)`

**해결 방법**:
- Neo4j 버전을 5.13 이상으로 업그레이드
- 또는 Fallback 모드 사용 (수동 코사인 유사도 계산)

### 3. Ollama 연결 실패
**증상**: `❌ LLM 답변 생성 실패: ...`

**해결 방법**:
- Ollama 서비스 실행: `ollama serve`
- 모델 다운로드: `ollama pull exaone3.5:7.8b`
- `.env`의 `OLLAMA_BASE_URL` 확인

### 4. 메모리 부족
**증상**: Out of memory 에러

**해결 방법**:
- 배치 크기 조정
- Neo4j 메모리 설정 최적화
- 대용량 그래프의 경우 분할 처리

### 5. 검색 결과 없음
**증상**: `⚠️ 검색 결과가 없습니다`

**해결 방법**:
- `embed_youngmin7.py` 먼저 실행 (임베딩 추가)
- Neo4j에서 임베딩 확인:
  ```cypher
  MATCH (n) WHERE n.embedding IS NOT NULL RETURN count(n)
  ```

---

## 성능 최적화

### 임베딩 생성 속도
- **배치 처리**: 여러 개체를 동시에 임베딩
- **GPU 사용**: CUDA 활성화 시 5~10배 빠름
- **캐싱**: 이미 임베딩된 개체는 건너뛰기

### 검색 속도
- **벡터 인덱스**: Neo4j 5.13+ 사용 시 10배 이상 빠름
- **제한된 검색**: `top_k` 값 조정 (기본값: 5)
- **그래프 깊이**: `max_depth` 값 조정 (기본값: 2)

### 메모리 사용
- **모델 공유**: 여러 쿼리에서 동일 모델 재사용
- **연결 풀링**: Neo4j 드라이버 연결 풀 사용
- **컨텍스트 제한**: 과도한 컨텍스트 로드 방지

---

## 확장 가능성

### 1. 다른 임베딩 모델 사용
```python
embedder = GraphEmbedder('intfloat/multilingual-e5-large')
```

### 2. 다른 LLM 사용
```python
from llama_index.llms.openai import OpenAI
self.llm = OpenAI(model="gpt-4")
```

### 3. 커스텀 검색 전략
```python
def custom_search(self, query):
    # 도메인 특화 검색 로직
    pass
```

### 4. 다중 데이터베이스 지원
```python
qa_system = Youngmin7QASystem(database="youngmin8")
```

---

## 라이선스

MIT License

---

## 문의

문제가 발생하거나 기능 개선 제안이 있으시면 이슈를 등록해주세요.
