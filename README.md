# 조선왕조 GraphRAG 웹 애플리케이션 🏯

조선왕조 지식 그래프 기반 질의응답 시스템 (React + Flask + Neo4j)

## 🚀 빠른 시작

### 1단계: Python 의존성 설치
```powershell
pip install -r requirements.txt
```

### 2단계: Node.js 의존성 설치
```powershell
npm install
```

### 3단계: 서버 실행

**방법 A: 자동 실행 (권장)**
```powershell
.\scripts\start_web.ps1
```

**방법 B: 수동 실행**
```powershell
# 터미널 1: 백엔드
python backend/qa_api.py

# 터미널 2: 프론트엔드
npm start
```

브라우저에서 `http://localhost:3000` 자동으로 열림!

---

## 📁 프로젝트 구조

```
joseon_graphrag/
│
├── backend/                 # 🐍 Python 백엔드
│   ├── qa_api.py           # Flask API 서버
│   └── qa_multimodal.py    # QA 시스템 코어
│
├── src/                     # ⚛️ React 프론트엔드
│   ├── App.js              # 메인 컴포넌트
│   ├── App.css             # 스타일
│   └── index.js            # 엔트리 포인트
│
├── public/                  # 정적 파일
│   └── index.html
│
├── docs/                    # 📚 문서
│   ├── QUICKSTART_WEB.md   # 상세 가이드
│   └── WEB_START.md        # 간단 가이드
│
├── scripts/                 # 🔧 실행 스크립트
│   └── start_web.ps1       # 원클릭 실행
│
├── input/                   # 📖 원본 데이터
│   └── *.txt               # 조선왕조 텍스트
│
├── archive/                 # 📦 아카이브 (미사용)
│   ├── server.js           # 구 Node.js 서버
│   └── ...                 # 기타 테스트 파일
│
├── .env                     # 환경 변수
├── package.json            # Node.js 설정
└── requirements.txt        # Python 의존성
```

---

## 🎯 주요 기능

### 1️⃣ 다중 검색 모드
- **하이브리드** (권장): 벡터 + 키워드 + 그래프 통합
- **벡터 검색**: 의미적 유사도 기반
- **키워드 검색**: 정확한 키워드 매칭
- **Cypher 검색**: LLM이 자동 쿼리 생성

### 2️⃣ 실시간 그래프 시각화
- Mermaid.js 기반 깔끔한 다이어그램
- 노드 타입별 색상 구분
- 관계 라벨 표시

### 3️⃣ LLM 기반 답변
- Ollama (exaone3.5:7.8b) 사용
- 검색 결과 기반 정확한 답변 생성

---

## ⚙️ 환경 설정

`.env` 파일 확인:

```env
# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=qqqqqqqq
NEO4J_DATABASE=youngmin7

# Ollama
OLLAMA_MODEL=exaone3.5:7.8b
OLLAMA_BASE_URL=http://localhost:11434

# Flask
PORT=5001
```

---

## 📝 사용 예시

### 예시 질문:
- "세종의 아버지는?"
- "태종이 편찬한 책은?"
- "세조의 정치적 경쟁자는?"
- "임진왜란은 언제 발생했나?"

---

## 🛠️ 기술 스택

| 구분 | 기술 |
|------|------|
| **백엔드** | Python, Flask, Neo4j, Ollama |
| **프론트엔드** | React, Mermaid.js |
| **임베딩** | SentenceTransformer (ko-sroberta) |
| **LLM** | Exaone 3.5 (7.8B) |
| **그래프 DB** | Neo4j |

---

## 📚 문서

- [상세 가이드](docs/QUICKSTART_WEB.md) - 전체 설치 및 설정
- [빠른 시작](docs/WEB_START.md) - 최소 실행 가이드

---

## 🎨 커스터마이징

### 검색 모드 기본값 변경
`src/App.js`:
```javascript
const [mode, setMode] = useState('hybrid'); // 'vector', 'keyword', 'cypher'
```

### 그래프 레이아웃 변경
`src/App.js`:
```javascript
graph LR  // Left to Right (현재)
graph TB  // Top to Bottom (변경 시)
```

---

## 🐛 문제 해결

### Neo4j 연결 오류
```powershell
# Neo4j Desktop에서 youngmin7 데이터베이스 시작 확인
```

### Ollama 연결 오류
```powershell
ollama serve
ollama pull exaone3.5:7.8b
```

### 포트 충돌
```powershell
# .env 파일에서 PORT 변경
PORT=5002
```

---

## 📄 라이선스

MIT License

---

**즐거운 조선왕조 탐험! 🏯**
