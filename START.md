# 조선왕조 GraphRAG - 빠른 시작 가이드

##  5분 설치 (밀키트 방식)

### 1 필수 프로그램 설치 (한 번만)

#### Python 설치
https://www.python.org/downloads/
- Python 3.11 이상 다운로드
- 설치 시 'Add Python to PATH' 체크!

#### Ollama 설치
PowerShell에서 실행:
```powershell
winget install Ollama.Ollama
```
또는 https://ollama.com/download/windows

#### Neo4j Desktop 설치
https://neo4j.com/download/
1. 다운로드 후 설치
2. 새 데이터베이스 생성
3. 비밀번호: **qqqqqqqq** 입력
4. Plugins 탭  **APOC 설치** (중요!)
5. Start 버튼 클릭

---

### 2 모델 다운로드 (RTX 5070 최적화)

PowerShell에서 실행:
```powershell
ollama pull llama3.1:13b
```
 8.5GB 다운로드, 약 5-10분 소요

---

### 3 프로젝트 설정

이 폴더에서 PowerShell 실행:

```powershell
# 가상환경 생성
python -m venv .venv

# 가상환경 활성화
.venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt
```

---

### 4 실행!

```powershell
# 단일 파일 테스트 (세종)
python graph_builder.py input/4.세종.txt

# 전체 26개 왕 일괄 처리 (약 1-2시간 소요)
python batch_process.py
```

---

### 5 결과 확인

브라우저에서 http://localhost:7474 접속

**추천 쿼리:**
```cypher
# 전체 그래프 보기
MATCH p=()-[r]->() RETURN p LIMIT 100

# 세종 중심 그래프
MATCH p=(n:Entity {name: '세종'})-[*1..2]-() RETURN p

# 모든 왕 보기
MATCH (n:Entity) WHERE n.type = 'Person' RETURN n
```

---

##  문제 해결

**Ollama 느려질 때:**
```powershell
ollama stop
ollama serve
```

**Neo4j 연결 실패:**
- Neo4j Desktop에서 Start 클릭 확인
- APOC 플러그인 설치 확인
- .env 파일에서 비밀번호 확인

**Python 패키지 오류:**
```powershell
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

---

##  성능 정보

- **모델**: llama3.1:13b (최고 품질)
- **Context**: 8192 토큰
- **처리 속도**: 파일당 약 2-5분
- **GPU 사용률**: 70-90%

---

##  체크리스트

- [ ] Python 3.11+ 설치됨
- [ ] Ollama 설치 및 llama3.1:13b 다운로드 완료
- [ ] Neo4j Desktop 실행 중
- [ ] APOC 플러그인 설치됨
- [ ] 가상환경 생성 및 패키지 설치 완료
- [ ] .env 파일에 Neo4j 비밀번호 설정

모두 체크되었으면 python graph_builder.py 실행!
