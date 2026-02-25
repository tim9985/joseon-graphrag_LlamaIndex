# 🚀 조선왕조 GraphRAG 다중 검색 QA 시스템 - 빠른 시작

## ⚡ 1분 안에 시작하기

### 기본 실행 (대화형 모드)

```bash
# 벡터 모델 없이 빠르게 시작 (권장)
python qa_multimodal.py --no-vector

# 또는 벡터 포함 (초기화 시간 필요)
python qa_multimodal.py
```

### 단일 질문

```bash
# 키워드 검색 (빠름)
python qa_multimodal.py --no-vector -q "세종의 아버지는?" -m keyword

# Cypher 쿼리 (정확함)
python qa_multimodal.py --no-vector -q "세종의 아버지는?" -m cypher

# 하이브리드 (가장 정확함, 느림)
python qa_multimodal.py -q "세종의 아버지는?" -m hybrid
```

---

## 🎯 4가지 검색 모드

| 모드 | 명령어 | 특징 | 속도 |
|------|--------|------|------|
| **keyword** | `-m keyword` | 문자열 매칭, 빠름 | ⚡⚡⚡ |
| **cypher** | `-m cypher` | LLM이 Cypher 생성, 정확함 | ⚡⚡ |
| **vector** | `-m vector` | 의미 기반 검색 | ⚡ |
| **hybrid** | `-m hybrid` | 벡터+키워드+그래프 통합, 최고 정확도 | 🐢 |

---

## 📖 사용 예시

### 예시 1: 관계 질문

```bash
# 키워드 모드 (빠름)
python qa_multimodal.py --no-vector -m keyword -q "세종 아버지"

# Cypher 모드 (정확함)
python qa_multimodal.py --no-vector -m cypher -q "세종의 아버지는 누구인가?"
```

**기대 출력:**
```
================================================================================
💬 질문: 세종의 아버지는 누구인가?
🔍 검색 모드: CYPHER
================================================================================

⚙️ Cypher 쿼리 생성 및 실행 중...

생성된 Cypher 쿼리:
  MATCH (세종)-[:아버지]->(parent) RETURN parent.name

결과: 1개

================================================================================
💡 답변:
================================================================================
세종의 아버지는 태종입니다.
================================================================================
```

### 예시 2: 대화형 모드

```bash
python qa_multimodal.py --no-vector
```

**대화 예시:**
```
💬 질문 (hybrid): 세종의 아버지는?
# ... 답변 ...

💬 질문 (hybrid): /mode cypher
✓ 검색 모드 변경: CYPHER

💬 질문 (cypher): 태종의 업적은?
# ... 답변 ...

💬 질문 (cypher): /help
# 도움말 표시

💬 질문 (cypher): /exit
👋 시스템을 종료합니다.
```

### 예시 3: 배치 처리

```bash
# 질문 파일 생성
cat > questions.txt << EOF
세종의 아버지는?
태종의 업적은?
임진왜란은 누구 재위 중?
EOF

# 실행
python qa_multimodal.py --no-vector --batch questions.txt -m keyword
```

---

## 💡 팁

### 속도 최적화

```bash
# ⚡ 가장 빠름 (벡터 모델 스킵 + 키워드 모드)
python qa_multimodal.py --no-vector -m keyword -q "태종"

# 🐢 가장 느림 (벡터 로드 + 하이브리드)
python qa_multimodal.py -m hybrid -q "태종"
```

### 모드 선택 가이드

| 질문 유형 | 권장 모드 | 이유 |
|----------|----------|------|
| "세종의 아버지는?" | **cypher** | 명확한 관계 쿼리 |
| "태종" | **keyword** | 단순 개체 검색 |
| "훈민정음 만든 사람" | **vector** | 의미 기반 검색 |
| "조선 초기 주요 인물" | **hybrid** | 복잡한 추론 |

### 문제 해결

**검색 결과가 없을 때:**
```bash
# 1. 다른 모드 시도
python qa_multimodal.py --no-vector -m keyword -q "세종"

# 2. 키워드 확인
python qa_multimodal.py --no-vector -m keyword -q "世宗"  # ❌ 한자
python qa_multimodal.py --no-vector -m keyword -q "세종"  # ✅ 한글
```

**Cypher 쿼리 실패 시:**
```bash
# hybrid 모드 사용 (다른 검색 방법 자동 사용)
python qa_multimodal.py --no-vector -m keyword -q "성종 정치적 경쟁자"
```

---

## 🔧 전체 옵션

```bash
python qa_multimodal.py [옵션]

옵션:
  -m, --mode {vector|keyword|cypher|hybrid}
      검색 모드 (기본: hybrid)
  
  -q, --question TEXT
      단일 질문
  
  --batch FILE
      배치 모드: 질문 파일 경로
  
  --no-vector
      벡터 모델 로드 안 함 (빠른 시작)
  
  -v, --verbose
      상세 초기화 로그
  
  -h, --help
      도움말 표시
```

---

## 📚 더 알아보기

상세한 사용법은 [USAGE_qa_multimodal.md](USAGE_qa_multimodal.md)를 참고하세요.

---

**즐거운 질의응답 되세요! 🎉**
