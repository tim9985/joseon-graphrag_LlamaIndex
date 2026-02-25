# 🚀 Gemini API QA 시스템 빠른 시작 (5분)

Gemini API를 사용한 조선왕조 GraphRAG 질의응답 시스템을 5분 안에 실행해보세요!

## ⚡ 1단계: API 키 발급 (1분)

1. [Google AI Studio](https://aistudio.google.com/app/apikey) 접속
2. **"Create API Key"** 클릭
3. API 키 복사

## 📝 2단계: 환경 설정 (1분)

`.env` 파일을 열고 다음을 추가/수정:

```bash
GEMINI_API_KEY=여기에_복사한_API_키_붙여넣기

NEO4J_URI=bolt://127.0.0.1:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=qqqqqqqq
NEO4J_DATABASE=youngmin7
```

## 📦 3단계: 패키지 설치 (1분)

```bash
pip install google-generativeai
```

**주의:** 다른 패키지들(neo4j, python-dotenv 등)은 이미 설치되어 있을 것입니다.

## ✅ 4단계: Neo4j 확인 (1분)

Neo4j Desktop을 열고 `youngmin7` 데이터베이스가 **시작(Start)** 상태인지 확인하세요.

## 🎮 5단계: 실행! (1분)

### 간단 테스트

```bash
python test_qa_gemini.py
```

### 대화형 모드

```bash
python qa_gemini.py
```

그리고 질문해보세요:
```
💬 질문 (hybrid): 세종의 아버지는?
```

### 단일 질문 모드

```bash
python qa_gemini.py -q "태종이 편찬한 책은?" -m cypher
```

## 🎯 예상 결과

```
================================================================================
질문: 세종의 아버지는?
검색 모드: CYPHER
================================================================================

[Cypher 검색] Cypher 쿼리 생성 및 실행 중...

생성된 Cypher 쿼리:
  MATCH (세종)-[:아버지]->(father) RETURN father.name

결과: 1개

================================================================================
답변:
================================================================================
세종의 아버지는 태종입니다.
================================================================================
```

## ⚡ 비교 테스트

Gemini vs Ollama 성능 비교:

```bash
python compare_qa_systems.py
```

## 🔥 주요 기능

### 1. Cypher 모드 (추천!)

Gemini가 자연어를 Cypher 쿼리로 자동 변환:

```bash
python qa_gemini.py -q "성종의 정치적 경쟁자는?" -m cypher
```

### 2. 하이브리드 모드

벡터 + 키워드 + 그래프 통합 검색:

```bash
python qa_gemini.py -q "정조의 업적" -m hybrid
```

### 3. 키워드 모드 (가장 빠름)

```bash
python qa_gemini.py -q "훈민정음" -m keyword
```

## 📝 자주 묻는 질문

### Q: API 키가 무료인가요?

A: 네! Gemini API 무료 티어는:
- 분당 15회 요청
- 일일 1,500회 요청
- 개인 프로젝트에 충분

### Q: Ollama vs Gemini, 뭘 써야 하나요?

| 상황 | 추천 |
|------|------|
| 인터넷 연결 O, 정확도 중시 | **Gemini (qa_gemini.py)** |
| 로컬 환경, 무제한 사용 | **Ollama (qa_multimodal.py)** |
| 빠른 프로토타입 | **Gemini (qa_gemini.py)** |
| 프로덕션 (대량 요청) | **Ollama (qa_multimodal.py)** |

### Q: Rate Limit이 걸리면 어떻게 하나요?

A: 코드에서 자동으로 재시도합니다. 잠시 기다려주세요!

### Q: 벡터 검색을 사용하고 싶어요

A: 먼저 임베딩을 생성하세요:

```bash
python embed_youngmin7.py
```

그 후:
```bash
python qa_gemini.py -q "세종" -m vector
```

## 🎓 다음 단계

1. [README_GEMINI.md](README_GEMINI.md) - 전체 문서 읽기
2. 다양한 검색 모드 실험
3. 배치 모드로 여러 질문 처리
4. 나만의 질문 만들어보기

## 🆘 문제 발생?

### GEMINI_API_KEY 오류
```
ValueError: GEMINI_API_KEY 환경변수가 설정되지 않았습니다.
```
→ `.env` 파일 확인!

### Neo4j 연결 실패
```
[오류] Neo4j 연결 실패
```
→ Neo4j Desktop에서 데이터베이스 시작!

### google-generativeai 없음
```
❌ google-generativeai 패키지가 없습니다.
```
→ `pip install google-generativeai`

## 🎉 완료!

이제 Gemini API를 사용한 조선왕조 GraphRAG를 사용할 수 있습니다!

**Tip:** 대화형 모드에서 `/help` 입력하면 전체 명령어를 볼 수 있습니다.

```bash
python qa_gemini.py

💬 질문 (hybrid): /help
```

---

**더 자세한 정보:** [README_GEMINI.md](README_GEMINI.md)
