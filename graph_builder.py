"""
조선왕조 GraphRAG 구축 - EXAONE 3.5 최적화 버전
LlamaIndex + Ollama (EXAONE 3.5 7.8B) + Neo4j
APOC 자동 감지 및 Fallback 지원
"""
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
from llama_index.llms.ollama import Ollama
import re
import time

load_dotenv()


def check_apoc_available(neo4j_driver, database):
    """APOC 플러그인 설치 여부 확인"""
    try:
        with neo4j_driver.session(database=database) as session:
            result = session.run("RETURN apoc.version() as version")
            version = result.single()
            if version:
                print(f"✓ APOC 플러그인 감지됨: {version['version']}")
                return True
    except Exception as e:
        print(f"⚠️  APOC 플러그인 미설치 (Fallback 모드 사용)")
        print(f"   설치 방법: Neo4j Desktop → Plugins → APOC 설치")
        return False
    return False


def extract_entities_and_relations(text: str, llm: Ollama):
    """고품질 한국어 개체 관계 추출 (llama3.1:14b 최적화)"""
    
    prompt = f"""다음 한국 역사 텍스트에서 모든 개체와 관계를 추출하세요.

[예시]
텍스트:
"광해군은 1608년 즉위하여 허준을 사면하고 내의원으로 복귀시켰다. 허준은 1610년 동의보감을 완성하여 왕에게 헌상하였다."

ENTITIES:
* 광해군 (Person) [재위_시작:1608, 재위_종료:1623, 칭호:조선_제15대_국왕, 묘호:광해군]
* 허준 (Person) [출생년:1539, 사망년:1615, 직업:의원, 본관:양천]
* 내의원 (Organization) [유형:의료기관, 소속:조선_왕실]
* 동의보감 (Artifact) [유형:의학서, 저자:허준, 완성년:1610]
* 1608년 (Date) [유형:연도]
* 1610년 (Date) [유형:연도]
* 광해군_즉위 (Event) [주체:광해군, 시기:1608년, 유형:즉위]
* 허준_사면 (Event) [주체:광해군, 대상:허준, 시기:1608년, 유형:사면]
* 동의보감_완성 (Event) [주체:허준, 결과물:동의보감, 시기:1610년, 유형:저술]
* 조선_왕실 (Organization) [유형:왕조, 성씨:전주_이씨]

RELATIONSHIPS:
* 광해군 -> 즉위함 -> 조선_제15대_국왕
* 광해군 -> 명령함 -> 허준_사면
* 광해군 -> 수령함 -> 동의보감
* 허준 -> 사면받음 -> 광해군
* 허준 -> 복귀함 -> 내의원
* 허준 -> 저술함 -> 동의보감
* 허준 -> 소속됨 -> 내의원
* 동의보감 -> 헌상됨 -> 광해군
* 내의원 -> 소속기관 -> 조선_왕실
* 조선_왕실 -> 통치자 -> 광해군
* 광해군_즉위 -> 발생시기 -> 1608년
* 광해군_즉위 -> 주체 -> 광해군
* 허준_사면 -> 발생시기 -> 1608년
* 허준_사면 -> 대상 -> 허준
* 허준_사면 -> 명령자 -> 광해군
* 동의보감_완성 -> 발생시기 -> 1610년
* 동의보감_완성 -> 주체 -> 허준
* 1608년 -> 시대배경 -> 광해군
* 1610년 -> 시대배경 -> 광해군

[실제 텍스트]
{text}

[추출 지침] (반드시 지키세요):

1. **한국어 전용 규칙** (절대 준수)
- 모든 개체명, 관계명, 속성명, 속성값은 **100% 한국어**로만 작성하세요.
- 영어 단어 사용 절대 금지
- 단, 타입 표시는 예시처럼 영어 사용: (Person), (Organization) 등

2. **개체 추출**
다음 유형의 개체를 모두 추출하세요.
- Person: 왕, 신하, 장군, 학자, 승려, 백성 등
- Organization: 관청, 부서, 단체, 왕조, 세력
- Location: 도시, 지역, 성, 궁궐, 건물
- Date: 년/월/일, 특정 시기
- Event: 전쟁, 반란, 즉위, 사망, 개혁, 법 제정, 책 편찬 등
- Concept: 제도, 정책, 사상, 이념
- Artifact: 책, 문서, 무기, 건축물
- Title: 관직명, 칭호, 묘호, 시호

**예시:**
- ✅ 좋은 예: "세종 (Person)", "의정부 (Organization)", "임진왜란 (Event)"
- ❌ 나쁜 예: "King Sejong (Person)", "세宗 (Person)" "Cabinet (Organization)"

3. **개체 이름 정규화 (동일 인물 병합)**

**핵심 원칙: 동일 인물은 단 하나의 이름으로만 표현합니다.**

A. **띄어쓰기 통일**
- ✅ 좋은 예: "조선_왕실", "의정부_영의정", "경복궁_근정전"
- ❌ 나쁜 예: "조선 왕실", "의정부 영의정", "경복궁 근정전"

B. **왕/국왕 이름 통일 규칙** (매우 중요!)
동일 인물의 여러 이름 중 **묘호 또는 호(號)**로만 통일하세요.

**필수 통일 규칙:**
- 태조: "이성계", "태조 이성계" → **"태조"**로 통일
- 태종: "이방원", "태종 이도", "정안군" → **"태종"**으로 통일
- 세종: "이도", "세종대왕", "충녕대군" → **"세종"**으로 통일
- 문종: "이향", "세자 이향" → **"문종"**으로 통일
- 단종: "이홍위", "노산군" → **"단종"**으로 통일
- 세조: "이유", "수양대군" → **"세조"**로 통일
- 성종: "이혈", "자을산군" → **"성종"**으로 통일
- 연산군: "이융" → **"연산군"**으로 통일
- 중종: "이역", "진성대군" → **"중종"**으로 통일
- 선조: "이연", "하성군" → **"선조"**로 통일
- 광해군: "이혼" → **"광해군"**으로 통일
- 인조: "이종", "능양군" → **"인조"**로 통일
- 효종: "이호", "봉림대군" → **"효종"**으로 통일
- 영조: "이금", "연잉군" → **"영조"**로 통일
- 정조: "이산", "세손 이산" → **"정조"**로 통일
- 철종: "이원범", "강화도령" → **"철종"**으로 통일

**예시:**
- ✅ 좋은 예: 텍스트에 "이방원이 왕위에 올라 태종이 되었다"라면
  → 개체: "태종 (Person)"만 생성
  → 관계: "태종 -> 즉위함 -> 조선_제3대_국왕"

- ❌ 나쁜 예: "이방원 (Person)"과 "태종 (Person)"을 별도 개체로 생성
  → 이렇게 하면 그래프가 분열됩니다!

C. **대명사 구체화**
- ✅ 좋은 예: "왕", "상감", "전하" → 해당 시기 국왕 이름으로 교체
- ❌ 나쁜 예: "왕 (Person)", "상감 (Person)" 그대로 사용

D. **일반 인물 통일**
- ✅ 좋은 예: "이순신", "충무공" → **"이순신"**으로 통일
- ✅ 좋은 예: "정도전", "삼봉" → **"정도전"**으로 통일
- ❌ 나쁜 예: "이순신 (Person)"과 "충무공 (Person)"을 별도로 생성

4. **관계 추출 - 구체적이고 한국어로**

**형식:** 주체 -> 관계명 -> 대상

A. **관계명 규칙**
- 반드시 **구체적인 한국어 동사/명사**로만 작성
- 추상적이거나 모호한 표현 금지

**예시:**
- ❌ 나쁜 예: "연관됨", "관련됨", "관계있음", "속함"
- ✅ 좋은 예: "즉위함", "사면함", "저술함", "아들", "소속됨", "통치함"

B. **필수 관계 타입 (모두 한국어)**

**통치/정치 관계:**
- ✅ 좋은 예: "즉위함", "폐위함", "등용함", "파면함", "사면함", "명령함", "통치함", "책봉함"
- ❌ 나쁜 예: "왕이됨", "정치함", "다스림"

**가족 관계:**
- ✅ 좋은 예: "아버지", "어머니", "아들", "딸", "배우자", "형제", "조부", "손자", "왕비"
- ❌ 나쁜 예: "가족", "친척", "혈연", "왕가"

**소속 관계:**
- ✅ 좋은 예: "소속됨", "소속기관", "관할함", "산하조직", "통치자", "책임자"
- ❌ 나쁜 예: "속함", "포함됨", "연결됨"

**시간 관계:**
- ✅ 좋은 예: "발생시기", "재위기간", "활동시기", "시대배경", "선대", "후대", "계승함"
- ❌ 나쁜 예: "시간", "시기", "때"

**공간 관계:**
- ✅ 좋은 예: "위치함", "이동함", "거주함", "전장", "수도", "건설지", "영토"
- ❌ 나쁜 예: "장소", "공간", "지역"

**인과 관계:**
- ✅ 좋은 예: "원인", "결과", "영향미침", "계기됨", "유발함", "초래함"
- ❌ 나쁜 예: "때문", "결과적", "이유"

**창작 관계:**
- ✅ 좋은 예: "저술함", "편찬함", "건설함", "제작함", "완성함", "창제함", "발명함"
- ❌ 나쁜 예: "만듦", "작성", "생산"

5. **국왕 중심 거대 연결 네트워크 구축 (최우선)**

**핵심 원칙: 텍스트의 모든 개체는 반드시 국왕과 연결되어야 합니다.**

A. **직접 연결 (1-hop)** - 국왕과 직접 연결:
- 왕실 가족, 핵심 신하, 왕명 정책/사건, 왕실 조직

**예시:**
- ✅ 좋은 예: "허준 -> 어의 -> 세종", "집현전 -> 설치자 -> 세종"
- ❌ 나쁜 예: "허준 (Person)"만 생성하고 국왕과 연결 안 함

B. **2단계 연결 (2-hop)** - 중간 매개를 통해 연결:
- 일반 신하/관료 → 소속 부서 → 국왕
- 지방 인물 → 지역 조직 → 국왕
- 백성/일반인 → 정책/사건 → 국왕

**예시:**
- ✅ 좋은 예: "황희 -> 소속됨 -> 의정부", "의정부 -> 통치자 -> 세종"
- ❌ 나쁜 예: "황희 -> 관련됨 -> 세종" (구체적이지 않음)

C. **3단계 연결 (3-hop)** - 모든 잔여 개체를 연결:
- 물건/유물 → 제작사업 → 담당부서 → 국왕
- 개념/제도 → 관련사건 → 담당조직 → 국왕
- 날짜 → 사건 → 주체/명령자 → 국왕

**예시:**
- ✅ 좋은 예: 
  "훈민정음 -> 창제자 -> 세종"
  "1446년 -> 시대배경 -> 세종"
  "집현전 -> 소속기관 -> 조선_왕실 -> 통치자 -> 세종"
- ❌ 나쁜 예: "훈민정음 (Artifact)"만 생성하고 관계 없음

D. **강제 연결 메커니즘** (고립 노드 제로)

모든 개체는 **반드시 최소 2개 이상의 관계**를 가져야 합니다.
직접 연결이 어려운 개체는 다음 관계를 사용:

**시대배경 관계 (Date/Event → 국왕):**
- ✅ 좋은 예: "1408년 -> 시대배경 -> 태종"
- ✅ 좋은 예: "제1차_왕자의_난 -> 시대배경 -> 태조"
- ❌ 나쁜 예: "1408년 (Date)"만 생성

**통치자 관계 (Organization → 국왕):**
- ✅ 좋은 예: "의정부 -> 소속기관 -> 조선_왕실 -> 통치자 -> 세종"
- ❌ 나쁜 예: "의정부 (Organization)"만 생성

**재위중 관계 (Event → 국왕):**
- ✅ 좋은 예: "한양천도 -> 재위중 -> 태조"
- ✅ 좋은 예: "계유정난 -> 재위중 -> 단종"

**활동시기 관계 (Person → 국왕):**
- ✅ 좋은 예: "이순신 -> 활동시기 -> 선조"
- ✅ 좋은 예: "황희 -> 활동시기 -> 세종"

6. **고립 커뮤니티 방지 - 브릿지 개체 생성**

작은 커뮤니티가 형성될 경우, **브릿지 개체**를 통해 메인 그래프와 연결:

A. **조선_왕실을 허브로 활용**
- 모든 Organization은 "조선_왕실"과 연결
- 조선_왕실은 해당 시기 국왕과 "통치자" 관계

**예시:**
- ✅ 좋은 예:
  "육조 -> 소속기관 -> 조선_왕실"
  "조선_왕실 -> 통치자 -> 태종"
- ❌ 나쁜 예: "육조 (Organization)"만 생성

B. **양방향 관계 필수 생성**

모든 단방향 관계는 반대 관계도 생성하세요.

**가족 관계 양방향:**
- ✅ 좋은 예:
  "태종 -> 아버지 -> 태조"
  "태조 -> 아들 -> 태종"

**스승-제자 관계 양방향:**
- ✅ 좋은 예:
  "세종 -> 스승 -> 권근"
  "권근 -> 제자 -> 세종"

**저작 관계 양방향:**
- ✅ 좋은 예:
  "허준 -> 저술함 -> 동의보감"
  "동의보감 -> 저자 -> 허준"

**소속 관계 양방향:**
- ✅ 좋은 예:
  "황희 -> 소속됨 -> 의정부"
  "의정부 -> 구성원 -> 황희"

**예시:**
- ❌ 나쁜 예: "A -> 아버지 -> B"만 생성
- ✅ 좋은 예: "A -> 아버지 -> B" + "B -> 아들 -> A" 둘 다 생성

7. **출력 품질 검증**

다음 체크리스트를 모두 만족해야 합니다:

□ 모든 개체명/관계명이 100% 한국어인가?
□ 동일 인물이 여러 이름으로 중복 생성되지 않았는가?
□ 모든 개체가 최소 2개 이상의 관계를 가지는가?
□ 국왕과 직간접으로 연결되지 않은 개체가 있는가?
□ 양방향 관계가 모두 생성되었는가?
□ 추상적 관계명("연관됨" 등)을 사용하지 않았는가?

[출력 형식] (엄격히 준수)
ENTITIES:
* 개체이름 (Type) [속성:값, ...]

RELATIONSHIPS:
* 주체 -> 관계명 -> 대상

* 위 두 섹션만 출력하고, 다른 설명은 절대 포함하지 마세요.
* 모든 관계명은 한국어 동사/명사형으로만 작성하세요.
* 동일 인물은 단 하나의 이름으로만 통일하세요.
"""
    
    try:
        print("\n🤖 llama3.1:14b 추론 시작...")
        start_time = time.time()
        
        response = llm.complete(prompt)
        
        elapsed_time = time.time() - start_time
        print(f"✓ LLM 응답 완료 (길이: {len(response.text)}자, 소요시간: {elapsed_time:.1f}초)")
        
        # 응답 미리보기 (디버깅용)
        print("\n📝 LLM 응답 미리보기:")
        print("-" * 80)
        preview_length = min(800, len(response.text))
        print(response.text[:preview_length])
        if len(response.text) > preview_length:
            print("...")
        print("-" * 80)
        
        return parse_response(response.text)
    except Exception as e:
        print(f"❌ LLM 추론 실패: {e}")
        import traceback
        traceback.print_exc()
        return [], []


def normalize_entity_name(name: str) -> str:
    """개체 이름 정규화"""
    name = name.replace(' ', '')
    name = name.replace('jong', '종')
    name = name.replace('Jong', '종')
    return name


def parse_response(response_text: str):
    """LLM 응답 파싱"""
    entities = []
    relations = []
    
    lines = response_text.split('\n')
    in_entities = False
    in_relations = False
    
    for line in lines:
        line = line.strip()
        
        if 'ENTITIES' in line.upper():
            in_entities = True
            in_relations = False
            continue
        elif 'RELATIONSHIPS' in line.upper():
            in_entities = False
            in_relations = True
            continue
        
        if in_entities and line.startswith('*'):
            match = re.search(r'\*\s+(.+?)\s+\((\w+)\)', line)
            if match:
                name = normalize_entity_name(match.group(1).strip())
                entity_type = match.group(2).strip()
                entities.append({"name": name, "type": entity_type})
        
        elif in_relations and line.startswith('*'):
            match = re.search(r'\*\s+(.+?)\s+->\s+(.+?)\s+->\s+(.+?)$', line)
            if match:
                source = normalize_entity_name(match.group(1).strip())
                relation = match.group(2).strip()
                target = normalize_entity_name(match.group(3).strip())
                relations.append({
                    "source": source,
                    "relation": relation,
                    "target": target
                })
    
    # 관계에 등장하는 개체 자동 추가
    entity_names = {e['name'] for e in entities}
    
    for rel in relations:
        if rel['source'] not in entity_names:
            entities.append({"name": rel['source'], "type": "Unknown"})
            entity_names.add(rel['source'])
        
        if rel['target'] not in entity_names:
            entities.append({"name": rel['target'], "type": "Unknown"})
            entity_names.add(rel['target'])
    
    print(f"\n🔍 파싱 결과: {len(entities)}개 개체, {len(relations)}개 관계 추출됨")
    
    if len(entities) == 0 and len(relations) == 0:
        print("⚠️  경고: 추출된 개체/관계가 없습니다!")
    
    return entities, relations


def save_to_neo4j_with_apoc(entities, relations, session):
    """APOC 사용 버전 (동적 관계 타입)"""
    print("\n🔗 관계 저장 중 (APOC 모드)...")
    relation_count = 0
    
    for i, rel in enumerate(relations, 1):
        try:
            rel_type = rel['relation'].strip()
            rel_type = rel_type.replace(' ', '_').replace('/', '_').replace('-', '_')
            
            session.run(
                """
                MATCH (s:Entity {name: $source})
                MATCH (t:Entity {name: $target})
                CALL apoc.create.relationship(s, $relType, {}, t) 
                YIELD rel
                RETURN rel
                """,
                source=rel['source'],
                target=rel['target'],
                relType=rel_type
            )
            relation_count += 1
            
            if i % 100 == 0:
                print(f"   {i}/{len(relations)} 관계 저장 완료...")
                
        except Exception as e:
            print(f"   관계 저장 실패: {rel['source']} -> {rel['relation']} -> {rel['target']}")
    
    return relation_count


def save_to_neo4j_without_apoc(entities, relations, session):
    """APOC 없이 저장 (Fallback 모드)"""
    print("\n🔗 관계 저장 중 (Fallback 모드 - 관계를 속성으로 저장)...")
    relation_count = 0
    
    for i, rel in enumerate(relations, 1):
        try:
            # 관계 타입을 RELATED_TO로 통일하고, 실제 관계명은 속성으로 저장
            session.run(
                """
                MATCH (s:Entity {name: $source})
                MATCH (t:Entity {name: $target})
                MERGE (s)-[r:RELATED_TO {type: $relation}]->(t)
                """,
                source=rel['source'],
                target=rel['target'],
                relation=rel['relation']
            )
            relation_count += 1
            
            if i % 100 == 0:
                print(f"   {i}/{len(relations)} 관계 저장 완료...")
                
        except Exception as e:
            print(f"   관계 저장 실패: {rel['source']} -> {rel['relation']} -> {rel['target']}")
    
    return relation_count


def save_to_neo4j(entities, relations, neo4j_driver, database):
    """Neo4j에 그래프 저장 (APOC 자동 감지)"""
    
    with neo4j_driver.session(database=database) as session:
        # 개체 저장
        print("\n💾 개체 저장 중...")
        for i, entity in enumerate(entities, 1):
            session.run(
                """
                MERGE (e:Entity {name: $name})
                SET e.type = $type
                """,
                name=entity['name'],
                type=entity['type']
            )
            if i % 50 == 0:
                print(f"   {i}/{len(entities)} 개체 저장 완료...")
        
        # APOC 사용 가능 여부 확인 후 관계 저장
        use_apoc = check_apoc_available(neo4j_driver, database)
        
        if use_apoc:
            relation_count = save_to_neo4j_with_apoc(entities, relations, session)
        else:
            relation_count = save_to_neo4j_without_apoc(entities, relations, session)
        
        return relation_count


def validate_graph_connectivity(neo4j_driver, database):
    """그래프 연결성 검증"""
    
    print("\n" + "="*80)
    print("🔍 그래프 품질 검증")
    print("="*80)
    
    with neo4j_driver.session(database=database) as session:
        # 1. 고립 노드 확인
        orphan_nodes = session.run("""
            MATCH (n:Entity)
            WHERE NOT (n)-[]-()
            RETURN n.name as name, n.type as type
        """).data()
        
        if orphan_nodes:
            print(f"\n⚠️  고립 노드 발견: {len(orphan_nodes)}개")
            for node in orphan_nodes[:10]:
                print(f"   - {node['name']} ({node['type']})")
        else:
            print(f"\n✅ 고립 노드 없음 (모든 노드 연결됨)")
        
        # 2. 약한 연결 노드 확인
        weak_nodes = session.run("""
            MATCH (n:Entity)
            WITH n, COUNT {(n)-[]-()} as degree
            WHERE degree > 0 AND degree <= 3
            RETURN n.name as name, n.type as type, degree
            ORDER BY degree
            LIMIT 20
        """).data()
        
        if weak_nodes:
            print(f"\n⚠️  약한 연결 노드 (연결 3개 이하): {len(weak_nodes)}개")
            for node in weak_nodes[:10]:
                print(f"   - {node['name']} ({node['type']}): {node['degree']}개 연결")
        
        # 3. 국왕 중심성 확인
        kings = session.run("""
            MATCH (n:Entity)
            WHERE n.type = 'Person' AND (
                n.name CONTAINS '조' OR 
                n.name CONTAINS '종' OR 
                n.name CONTAINS '군' OR
                n.name CONTAINS '왕'
            )
            WITH n, COUNT {(n)-[]-()} as degree
            WHERE degree > 0
            RETURN n.name as name, degree
            ORDER BY degree DESC
            LIMIT 15
        """).data()
        
        if kings:
            print(f"\n👑 국왕 중심성 (연결 개수 TOP 15):")
            for king in kings:
                print(f"   - {king['name']}: {king['degree']}개 연결")
        
        # 4. 관계 타입 분포
        relation_types = session.run("""
            MATCH ()-[r]->()
            RETURN type(r) as relation_type, count(r) as count
            ORDER BY count DESC
            LIMIT 20
        """).data()
        
        print(f"\n📊 관계 타입 분포 (TOP 20):")
        for rt in relation_types:
            print(f"   - {rt['relation_type']}: {rt['count']}개")
        
        # 5. Fallback 모드인 경우 실제 관계명 확인
        if relation_types and relation_types[0]['relation_type'] == 'RELATED_TO':
            print(f"\n   ℹ️  Fallback 모드 사용 중 - 실제 관계명 확인:")
            actual_relations = session.run("""
                MATCH ()-[r:RELATED_TO]->()
                RETURN DISTINCT r.type as actual_type, count(r) as count
                ORDER BY count DESC
                LIMIT 15
            """).data()
            for ar in actual_relations:
                print(f"      - {ar['actual_type']}: {ar['count']}개")


def build_graph(text_file: str = None, clear_db: bool = True):
    """그래프 구축 메인 함수 - EXAONE 3.5 최적화"""
    
    print("="*80)
    print("🚀 조선왕조 GraphRAG 구축 - EXAONE 3.5 최적화 버전")
    print("="*80)
    
    # EXAONE 3.5 7.8B 설정
    model_name = "exaone3.5:7.8b"
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    timeout = int(os.getenv("REQUEST_TIMEOUT", "600"))  # 10분
    context_window = 32768  # EXAONE 3.5 기본 컨텍스트
    
    llm = Ollama(
        model=model_name,
        base_url=base_url,
        request_timeout=timeout,
        context_window=context_window,
        temperature=0.1,  # 낮은 temperature로 안정적인 출력
    )
    print(f"✓ LLM 모델 초기화: {model_name}")
    print(f"  - Context Window: {context_window:,} 토큰")
    print(f"  - Timeout: {timeout}초")
    print(f"  - Temperature: 0.1 (안정성 우선)")
    
    # 텍스트 파일 선택
    import sys
    if text_file is None:
        if len(sys.argv) > 1:
            text_file = sys.argv[1]
        else:
            text_file = "input/4.세종.txt"
    
    # 텍스트 로드
    with open(text_file, 'r', encoding='utf-8') as f:
        text = f.read()
    
    print(f"\n📝 입력 파일: {text_file}")
    print(f"   텍스트 길이: {len(text):,}자")
    
    estimated_tokens = len(text) // 2  # 한글은 토큰 비율 다름
    print(f"   예상 토큰: ~{estimated_tokens:,} 토큰")
    
    if estimated_tokens > context_window * 0.5:
        print(f"⚠️  경고: 텍스트가 context window의 50%를 초과합니다!")
        print(f"   텍스트를 분할하여 처리하는 것을 권장합니다.")
    
    print("-"*80)
    print(text[:300] + "..." if len(text) > 300 else text)
    print("-"*80)
    
    # Neo4j 연결
    neo4j_uri = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
    neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "qqqqqqqq")
    neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")
    
    if not neo4j_password:
        raise ValueError("❌ NEO4J_PASSWORD가 .env 파일에 설정되지 않았습니다!")
    
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    if clear_db:
        print("\n🔄 Neo4j 데이터베이스 초기화 중...")
        with driver.session(database=neo4j_database) as session:
            session.run("MATCH (n) DETACH DELETE n")
        print("✓ 데이터베이스 초기화 완료")
    
    # 개체와 관계 추출
    print("\n🎯 개체와 관계 추출 중 (EXAONE 3.5 모드)...")
    print("   ⏱️  예상 소요 시간: 3-7분")
    print("   ✨ EXAONE 3.5는 한국어 처리에 최적화되어 있습니다.")
    
    entities, relations = extract_entities_and_relations(text, llm)
    
    print(f"\n✓ 추출 완료: {len(entities):,}개 개체, {len(relations):,}개 관계")
    
    # Neo4j에 저장
    relation_count = save_to_neo4j(entities, relations, driver, neo4j_database)
    print(f"\n✓ 저장 완료: {len(entities)}개 노드, {relation_count}개 관계")
    
    # 통계 확인
    print("\n" + "="*80)
    print("📊 그래프 통계")
    print("="*80)
    
    with driver.session(database=neo4j_database) as session:
        node_count = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
        rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]
        
        print(f"\n총 노드 수: {node_count:,}개")
        print(f"총 관계 수: {rel_count:,}개")
        
        # 노드 타입별
        print("\n노드 타입별 분포:")
        node_types = session.run("""
            MATCH (n:Entity)
            RETURN n.type as type, count(n) as count
            ORDER BY count DESC
        """).data()
        for nt in node_types:
            print(f"  - {nt['type']}: {nt['count']:,}개")
        
        # 샘플 트리플
        print(f"\n샘플 트리플 (처음 30개):")
        triples = session.run("""
            MATCH (s)-[r]->(o)
            RETURN s.name as subject, type(r) as relation, o.name as object
            LIMIT 30
        """).data()
        
        for i, t in enumerate(triples, 1):
            print(f"  {i}. {t['subject']} → {t['relation']} → {t['object']}")
    
    # 그래프 품질 검증
    validate_graph_connectivity(driver, neo4j_database)
    
    driver.close()
    
    print("\n" + "="*80)
    print("✅ 완료!")
    print("="*80)
    print(f"Neo4j Browser: http://localhost:7474")
    print(f"\n추천 쿼리:")
    print(f"  # 전체 그래프 구조")
    print(f"  MATCH p=()-[r]->() RETURN p LIMIT 100")
    print(f"  ")
    print(f"  # 국왕 중심 네트워크")
    print(f"  MATCH (k:Entity) WHERE k.type = 'Person' AND k.name CONTAINS '종'")
    print(f"  MATCH p=(k)-[*1..2]-() RETURN p LIMIT 200")
    
    return {
        "entities": len(entities),
        "relations": relation_count,
        "file": text_file
    }


if __name__ == "__main__":
    build_graph()
