# 조선왕조 GraphRAG 프로젝트

LlamaIndex + Ollama + Neo4j를 활용한 한국어 역사 텍스트 지식 그래프 구축

##  빠른 시작 (밀키트 방식)

### 1단계: 필수 프로그램 설치

#### Python 3.11+
https://www.python.org/downloads/

#### Ollama
```powershell
winget install Ollama.Ollama
```

#### Neo4j Desktop
https://neo4j.com/download/
- 설치 후 데이터베이스 생성
- 비밀번호를 **qqqqqqqq**로 설정 (또는 원하는 비밀번호 사용 후 .env 파일 수정)
- **APOC 플러그인 설치 필수!** (Plugins 탭에서 APOC 설치)

### 2단계: 모델 다운로드 (RTX 5070 최적화)

```powershell
# 고품질 13B 모델 (권장)
ollama pull llama3.1:13b

# 또는 빠른 8B 모델
ollama pull llama3.1:8b
```

### 3단계: 프로젝트 설정

```powershell
# 이 폴더에서 실행
cd joseon_graphrag

# 가상환경 생성
python -m venv .venv

# 가상환경 활성화
.venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt

# .env 파일 생성 (예제 복사)
Copy-Item .env.example .env
```

### 4단계: 실행!

```powershell
# 단일 파일 처리
python graph_builder.py input/4.세종.txt

# 전체 26개 왕 일괄 처리
python batch_process.py
```

### 5단계: 결과 확인

브라우저에서 http://localhost:7474 접속

```cypher
# 전체 그래프 보기
MATCH p=()-[r]->() RETURN p LIMIT 100

# 특정 왕 중심 그래프
MATCH p=(n:Entity {name: '세종'})-[*1..2]-() RETURN p
```

##  시스템 요구사항

- **RAM**: 32GB (권장)
- **GPU**: RTX 5070 또는 동급 (12GB+ VRAM)
- **저장공간**: 20GB 이상

##  성능 설정 (RTX 5070 최적화)

- 모델: llama3.1:13b (8.5GB, 최고 품질)
- Context Window: 8192 토큰
- Timeout: 300초
- GPU 가속 자동 활성화

##  문제 해결

### Ollama 느려짐
```powershell
ollama stop
ollama serve
```

### Neo4j 연결 실패
- Neo4j Desktop에서 데이터베이스 Start 확인
- APOC 플러그인 설치 확인

### GPU 인식 안됨
- NVIDIA 드라이버 최신 버전 설치

##  프로젝트 구조

```
joseon_graphrag/
 .env                 # 환경 변수 (Neo4j 비밀번호)
 requirements.txt     # Python 패키지
 graph_builder.py     # 단일 파일 처리
 batch_process.py     # 전체 일괄 처리
 input/               # 26개 왕 텍스트 파일
 README.md            # 이 파일
```

##  문의

문제 발생시 이슈 등록
