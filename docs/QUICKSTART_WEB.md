# 조선왕조 GraphRAG 웹 애플리케이션 빠른 시작 가이드

## 🌐 개요

이 웹 애플리케이션은 조선왕조 지식 그래프를 기반으로 사용자 질문에 답변하는 대화형 시스템입니다.

**주요 기능:**
- ✅ 다중 검색 모드 (벡터/키워드/Cypher/하이브리드)
- ✅ 실시간 그래프 시각화 (React Flow)
- ✅ LLM 기반 자연어 답변
- ✅ REST API 백엔드 (Flask)
- ✅ 반응형 React 프론트엔드

---

## 📋 사전 요구사항

### 1. 시스템 요구사항
- **Python 3.9+**
- **Node.js 16+** (npm 포함)
- **Neo4j Desktop** (데이터베이스)
- **Ollama** (LLM 서버)

### 2. 설치 확인
```powershell
# Python 버전 확인
python --version

# Node.js 버전 확인
node --version
npm --version

# Ollama 실행 확인
ollama list
```

---

## 🚀 설치 및 실행

### 1단계: Python 의존성 설치

```powershell
# 프로젝트 디렉토리로 이동
cd C:\Users\timjj\Desktop\joseon_graphrag

# 가상환경 생성 (선택)
python -m venv venv
.\venv\Scripts\Activate.ps1

# 의존성 설치
pip install -r requirements.txt

# Flask 추가 설치 (requirements.txt에 없는 경우)
pip install flask flask-cors
```

### 2단계: Node.js 의존성 설치

```powershell
# React 프론트엔드 의존성 설치
npm install
```

### 3단계: 환경 변수 설정

`.env` 파일을 확인하고 필요시 수정:

```env
# Neo4j 설정
NEO4J_URI=bolt://sungjun:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=qqqqqqqq
NEO4J_DATABASE=youngmin7

# Ollama 설정
OLLAMA_MODEL=exaone3.5:7.8b
OLLAMA_BASE_URL=http://localhost:11434

# Flask 서버 포트
PORT=5001
```

### 4단계: Neo4j 및 Ollama 실행

#### Neo4j 실행:
1. Neo4j Desktop 실행
2. `youngmin7` 데이터베이스 시작
3. 데이터가 없으면 그래프 구축:
   ```powershell
   python graph_builder.py
   ```

#### Ollama 실행:
```powershell
# Ollama 서버 시작 (별도 터미널)
ollama serve

# 모델 다운로드 (처음만)
ollama pull exaone3.5:7.8b
```

---

## 🎮 실행

### 방법 1: 두 개의 터미널 사용 (권장)

#### 터미널 1: Python 백엔드
```powershell
# Flask API 서버 실행
python qa_api.py
```

출력 예시:
```
================================================================================
조선왕조 GraphRAG API 서버 초기화 중...
================================================================================
LLM 로드 중...
임베딩 모델 로드 중...
Neo4j 연결 중...
초기화 완료!
================================================================================

🚀 조선왕조 GraphRAG API 서버 시작
   포트: 5001
   엔드포인트: http://localhost:5001/api/ask
   헬스체크: http://localhost:5001/api/health
================================================================================
```

#### 터미널 2: React 프론트엔드
```powershell
# React 개발 서버 실행
npm start
```

자동으로 브라우저가 열리면서 `http://localhost:3000` 접속됨

### 방법 2: 통합 실행 스크립트

`start_web.ps1` 파일 생성:
```powershell
# start_web.ps1
$backendJob = Start-Job -ScriptBlock { python qa_api.py }
$frontendJob = Start-Job -ScriptBlock { npm start }

Write-Host "백엔드와 프론트엔드 시작됨"
Write-Host "종료하려면 Ctrl+C 누르기"

Receive-Job -Job $backendJob -Wait
Receive-Job -Job $frontendJob -Wait
```

실행:
```powershell
.\start_web.ps1
```

---

## 🧪 테스트

### 1. 백엔드 API 테스트

```powershell
# 헬스체크
curl http://localhost:5001/api/health

# 질문 테스트
curl -X POST http://localhost:5001/api/ask `
  -H "Content-Type: application/json" `
  -d '{"question": "세종의 아버지는?", "mode": "hybrid"}'
```

### 2. 프론트엔드 사용

1. 브라우저에서 `http://localhost:3000` 접속
2. 왼쪽 패널에서 검색 모드 선택
3. 질문 입력 (예: "세종의 아버지는?")
4. "질문 보내기" 클릭
5. 오른쪽 패널에서 답변 및 그래프 확인

---

## 🎨 검색 모드 설명

| 모드 | 설명 | 사용 예시 |
|------|------|-----------|
| **하이브리드** | 벡터 + 키워드 + 그래프 통합 검색 (가장 정확) | 모든 질문에 적합 |
| **벡터 검색** | 의미적 유사도 기반 검색 | "효종의 아버지" |
| **키워드 검색** | 정확한 키워드 매칭 | "태종", "세종" |
| **Cypher 검색** | LLM이 자동으로 Cypher 쿼리 생성 | "세종이 편찬한 책은?" |

---

## 📁 프로젝트 구조

```
joseon_graphrag/
├── qa_api.py              # Flask 백엔드 API 서버 ⭐NEW
├── qa_multimodal.py       # QA 시스템 코어 로직
├── package.json           # Node.js 의존성
├── requirements.txt       # Python 의존성 (Flask 추가됨) ⭐
├── .env                   # 환경 변수
│
├── src/                   # React 프론트엔드 ⭐UPDATED
│   ├── App.js            # 메인 컴포넌트 (검색 모드 추가)
│   ├── App.css           # 스타일 (mode-selector 추가)
│   ├── index.js          # React 엔트리 포인트
│   └── ...
│
├── public/                # 정적 파일
│   └── index.html
│
└── input/                 # 원본 텍스트 데이터
    ├── 1.태조.txt
    ├── 2.정종.txt
    └── ...
```

---

## 🔧 문제 해결

### 1. 포트 충돌
```powershell
# 5001 포트가 사용 중이면 다른 포트로 변경
$env:PORT="5002"
python qa_api.py
```

`package.json`의 proxy도 변경:
```json
"proxy": "http://localhost:5002"
```

### 2. Neo4j 연결 실패
```powershell
# Neo4j 상태 확인
# Neo4j Desktop에서 데이터베이스가 실행 중인지 확인

# 연결 테스트
python check_db.py
```

### 3. Ollama 연결 실패
```powershell
# Ollama 서버 재시작
ollama serve

# 모델 다운로드 확인
ollama list
```

### 4. 임베딩 모델 로드 실패
```powershell
# 벡터 검색 비활성화하고 실행
# qa_api.py 수정:
qa_system = MultiModalQASystem(use_vector=False, verbose=True)
```

### 5. CORS 오류
- `flask-cors`가 설치되었는지 확인:
  ```powershell
  pip install flask-cors
  ```

### 6. React 빌드 오류
```powershell
# node_modules 재설치
rm -r node_modules package-lock.json
npm install
```

---

## 🎯 사용 예시

### 예시 질문들:

1. **가족 관계**
   - "세종의 아버지는?"
   - "태종의 아들은 누구인가?"

2. **업적 관련**
   - "세종이 편찬한 책은?"
   - "태종이 설치한 기관은?"

3. **정치 관련**
   - "세조의 정치적 경쟁자는?"
   - "성종의 통치 기간은?"

4. **사건 관련**
   - "임진왜란은 언제 발생했나?"
   - "계유정난의 주도자는?"

---

## 📊 성능 최적화

### 백엔드 최적화:
```python
# qa_api.py에서 검색 결과 개수 조정
search_results = qa_system.hybrid_search(question, top_k=10)  # 기본 15 → 10
```

### 프론트엔드 최적화:
```javascript
// App.js에서 그래프 노드 개수 제한
const limitedNodes = graphData.nodes.slice(0, 20);
```

---

## 🚀 프로덕션 배포

### 백엔드 (Flask):
```powershell
# Gunicorn 설치
pip install gunicorn

# 프로덕션 실행
gunicorn -w 4 -b 0.0.0.0:5001 qa_api:app
```

### 프론트엔드 (React):
```powershell
# 빌드
npm run build

# 정적 파일 서빙 (Node.js)
npm install -g serve
serve -s build -l 3000
```

---

## 📝 API 문서

### POST /api/ask
질문에 답변합니다.

**Request:**
```json
{
  "question": "세종의 아버지는?",
  "mode": "hybrid"
}
```

**Response:**
```json
{
  "answer": "세종의 아버지는 태종입니다...",
  "graphData": {
    "nodes": [
      {
        "id": "node_0",
        "labels": ["Person"],
        "properties": {
          "name": "세종",
          "score": 0.95
        }
      }
    ],
    "relationships": [
      {
        "id": "rel_0",
        "type": "아버지",
        "start": "node_0",
        "end": "node_1"
      }
    ]
  },
  "mode": "hybrid",
  "success": true
}
```

### GET /api/health
서버 상태를 확인합니다.

**Response:**
```json
{
  "status": "ok",
  "service": "joseon-graphrag-api",
  "qa_system": "initialized"
}
```

### GET /api/modes
사용 가능한 검색 모드 목록을 반환합니다.

---

## 🤝 기여

문제가 발생하거나 개선 사항이 있으면 이슈를 등록해주세요.

---

## 📄 라이선스

MIT License

---

**즐거운 조선왕조 탐험 되세요! 🏯**
