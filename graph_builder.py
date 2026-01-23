"""
조선왕조 GraphRAG 구축 (RTX 5070 최적화)
LlamaIndex + Ollama (llama3.1:13b) + Neo4j
"""
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.core import Settings, VectorStoreIndex, Document
import re

load_dotenv()


def extract_entities_and_relations(text: str, llm: Ollama):
    """고품질 한국어 개체 관계 추출 (llama3.1:13b 최적화)"""
    
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
* 광해군_즉위 -> 발생시기 -> 1608년
* 광해군_즉위 -> 주체 -> 광해군
* 허준_사면 -> 발생시기 -> 1608년
* 허준_사면 -> 대상 -> 허준
* 허준_사면 -> 명령자 -> 광해군
* 동의보감_완성 -> 발생시기 -> 1610년
* 동의보감_완성 -> 주체 -> 허준

[실제 텍스트]
{text}

[추출 지침] (반드시 지키세요):

1. 개체 추출
다음 유형의 개체를 모두 추출하세요.
- Person: 왕, 신하, 장군, 학자, 승려, 백성 등 사람 이름
- Organization: 관청, 부서, 단체, 왕조, 세력
- Location: 도시, 지역, 성, 전쟁터, 궁궐, 건물
- Date: 년/월/일, 연호, 특정 시기(예: 임진왜란_이전)
- Event: 전쟁, 반란, 즉위, 사망, 개혁, 법 제정, 책 편찬, 건설 등
- Concept: 제도, 정책, 사상, 이념, 법제, 세금 제도 등
- Artifact: 책, 문서, 무기, 건축물, 예술품 등
- Title: 관직명, 작위, 칭호, 묘호, 시호

* 가능한 한 암시된 개체도 추출합니다. (예: "백성들의 고통을 덜기 위해" → 백성, 고통)

2. 개체 이름 정규화
- 띄어쓰기를 제거하거나 언더스코어(_)로 통일합니다. (예: "조선 왕실" → "조선_왕실")
- 대명사나 호칭("왕", "상", "주상")은 해당 시기의 구체적인 국왕 이름(예: "세종")으로 바꿉니다.
- 동일 인물을 가리키는 여러 표현은 가장 보편적인 명칭 하나로 통일합니다.

3. 속성 기록
- 형식: [속성명:값, 속성명:값, ...]
- 값 안의 띄어쓰기는 언더스코어(_)로 대체합니다.

4. 관계 추출
- 형식: 주체 -> 관계명 -> 대상
- **중요:** 주체와 대상의 이름은 반드시 **ENTITIES 섹션에서 정의한 정규화된 개체명**과 정확히 일치해야 합니다.
- 주체나 대상이 여러 명일 경우(예: A와 B가 C를 공격), 묶지 말고 **각각 별도의 관계(Row)로 분리**하여 출력하세요.
- 관계명은 명확한 동사/명사형(예: "임명함", "저술함")을 사용하세요.
- 양방향 관계(아버지/아들, 스승/제자)를 적극적으로 생성하세요.

5. 국왕 중심 연결 및 고립 노드 금지 (핵심)
- **국왕 중심:** 텍스트가 다루는 시기의 국왕을 그래프의 중심 허브로 설정하세요. 모든 주요 개체는 국왕과 직간접적으로 연결되어야 합니다.
- **고립 금지:** 어떤 개체도 홀로 남지 않도록 [시대적_배경], [소속], [위치], [언급됨] 등의 관계를 사용하여 반드시 연결하세요.

6. 시간 정보 처리
- 텍스트의 모든 시간 정보는 Date 개체로 만들고, 관련 Event/Person과 연결하세요.

[출력 형식] (엄격히 준수)
ENTITIES:
* 개체이름 (Type) [속성:값, ...]

RELATIONSHIPS:
* 주체 -> 관계명 -> 대상

* 위 두 섹션만 출력하고, 다른 설명은 절대 포함하지 마세요.
"""
    
    try:
        print("\n🤖 LLM 추론 시작...")
        response = llm.complete(prompt)
        print(f"✓ LLM 응답 완료 (길이: {len(response.text)}자)")
        
        # 응답 미리보기 (디버깅용)
        print("\n📝 LLM 응답 미리보기:")
        print("-" * 80)
        print(response.text[:500] + "..." if len(response.text) > 500 else response.text)
        print("-" * 80)
        
        return parse_response(response.text)
    except Exception as e:
        print(f"❌ LLM 추론 실패: {e}")
        return [], []


def normalize_entity_name(name: str) -> str:
    """개체 이름 정규화 (공백 제거, 인코딩 수정 등)"""
    # 공백 제거
    name = name.replace(' ', '')
    # 인코딩 문제 수정
    name = name.replace('jong', '종'),
    name = name.replace('Jong', '종')
    return name


def parse_response(response_text: str):
    """LLM 응답 파싱 + 자동 보정"""
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
            # * 세종 (Person)
            match = re.search(r'\*\s+(.+?)\s+\((\w+)\)', line)
            if match:
                name = match.group(1).strip()
                name = normalize_entity_name(name)
                entity_type = match.group(2).strip()
                entities.append({"name": name, "type": entity_type})
        
        elif in_relations and line.startswith('*'):
            # * 세종 -> 직위 -> 제4대_국왕
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
    
    # 후처리: 관계에 등장하는 개체를 자동으로 추가
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
        print("   원인: 1) LLM이 형식을 따르지 않음")
        print("         2) 타임아웃으로 응답 불완전")
        print("         3) 모델이 프롬프트 이해 실패")
    
    return entities, relations


def save_to_neo4j(entities, relations, neo4j_driver, database):
    """Neo4j에 그래프 저장"""
    
    with neo4j_driver.session(database=database) as session:
        # 개체 저장
        for entity in entities:
            session.run(
                f"""
                MERGE (e:Entity {{name: $name}})
                SET e.type = $type
                """,
                name=entity['name'],
                type=entity['type']
            )
        
        # 관계 저장
        relation_count = 0
        for rel in relations:
            try:
                session.run(
                    """
                    MATCH (s:Entity {name: $source})
                    MATCH (t:Entity {name: $target})
                    MERGE (s)-[r:RELATES {type: $relation}]->(t)
                    """,
                    source=rel['source'],
                    target=rel['target'],
                    relation=rel['relation']
                )
                relation_count += 1
            except Exception as e:
                print(f"⚠️  관계 저장 실패: {rel['source']} -> {rel['target']}")
        
        return relation_count


def build_graph(text_file: str = None, clear_db: bool = True):
    """그래프 구축 메인 함수"""
    
    print("="*80)
    print("🚀 조선왕조 GraphRAG 구축 (RTX 5070 최적화)")
    print("="*80)
    
    # 고성능 LLM 설정 (RTX 3050 4GB VRAM 최적화)
    # 추천: llama3.1:8b (범용), exaone3.5:7.8b (한국어 강화)
    model_name = os.getenv("OLLAMA_MODEL", "exaone3.5:7.8b")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    timeout = int(os.getenv("REQUEST_TIMEOUT", "300"))
    context_window = int(os.getenv("CONTEXT_WINDOW", "8192"))
    
    llm = Ollama(
        model=model_name,
        base_url=base_url,
        request_timeout=timeout,
        context_window=context_window
    )
    print(f"✓ LLM 모델 초기화: {model_name}")
    
    # 텍스트 파일 선택
    import sys
    if text_file is None:
        if len(sys.argv) > 1:
            text_file = sys.argv[1]
        else:
            text_file = "input/4.세종.txt"  # 기본값
    
    # 텍스트 로드
    with open(text_file, 'r', encoding='utf-8') as f:
        text = f.read()
    
    print(f"\n📝 입력 파일: {text_file}")
    print(f"   텍스트 길이: {len(text):,}자")
    
    # Context window 체크
    max_chars = context_window * 3  # 대략적인 토큰-문자 비율 (1토큰 ≈ 3-4자)
    if len(text) > max_chars:
        print(f"⚠️  경고: 텍스트가 context window보다 큽니다!")
        print(f"   Context window: {context_window:,} 토큰 (약 {max_chars:,}자)")
        print(f"   텍스트 크기: {len(text):,}자")
        print(f"   → 일부 정보가 누락될 수 있습니다. CONTEXT_WINDOW를 늘리거나 청크 처리를 권장합니다.")
    
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
    print("\n🎯 개체와 관계 추출 중 (고품질 13B 모델 사용)...")
    print("   이 작업은 수 분이 걸릴 수 있습니다...")
    entities, relations = extract_entities_and_relations(text, llm)
    
    print(f"✓ 추출 완료: {len(entities):,}개 개체, {len(relations):,}개 관계")
    
    # Neo4j에 저장
    print("\n💾 Neo4j에 저장 중...")
    relation_count = save_to_neo4j(entities, relations, driver, neo4j_database)
    print(f"✓ 저장 완료: {len(entities)}개 노드, {relation_count}개 관계")
    
    # 통계 확인
    print("\n" + "="*80)
    print("📊 그래프 통계:")
    print("="*80)
    
    with driver.session(database=neo4j_database) as session:
        node_count = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
        rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]
        
        print(f"총 노드 수: {node_count}")
        print(f"총 관계 수: {rel_count}")
        
        # 노드 타입별
        print("\n노드 타입별:")
        node_types = session.run("""
            MATCH (n:Entity)
            RETURN n.type as type, count(n) as count
            ORDER BY count DESC
        """).data()
        for nt in node_types:
            print(f"  {nt['type']}: {nt['count']}개")
        
        # 샘플 트리플
        print(f"\n전체 트리플 ({rel_count}개):")
        triples = session.run("""
            MATCH (s)-[r]->(o)
            RETURN s.name as subject, r.type as relation, o.name as object
            ORDER BY subject
        """).data()
        
        for i, t in enumerate(triples, 1):
            print(f"  {i}. {t['subject']} → {t['relation']} → {t['object']}")
    
    driver.close()
    
    print("\n✅ 완료!")
    print("Neo4j Browser: http://localhost:7474")
    print("\n확인 쿼리:")
    print("  MATCH (n:Entity) RETURN n")
    print("  MATCH p=()-[r]->() RETURN p LIMIT 25")
    
    return {
        "entities": len(entities),
        "relations": relation_count,
        "file": text_file
    }


if __name__ == "__main__":
    build_graph()
