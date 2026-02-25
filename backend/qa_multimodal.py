"""
조선왕조 GraphRAG CLI QA 시스템
다중 검색 모드: 벡터/키워드/Cypher/글로벌(Louvain)/하이브리드
"""
import os
import sys
import argparse
import pickle
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from collections import defaultdict
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from neo4j import GraphDatabase
from llama_index.llms.ollama import Ollama
import numpy as np

load_dotenv()


@dataclass
class Community:
    """그래프 커뮤니티"""
    id: str
    nodes: List[str]
    summary: str
    level: int = 0

# SentenceTransformer는 필요할 때만 임포트 (초기화 시간 단축)
_SENTENCE_TRANSFORMER = None

def get_sentence_transformer():
    """SentenceTransformer 지연 로딩"""
    global _SENTENCE_TRANSFORMER
    if _SENTENCE_TRANSFORMER is None:
        from sentence_transformers import SentenceTransformer
        _SENTENCE_TRANSFORMER = SentenceTransformer('jhgan/ko-sroberta-multitask')
    return _SENTENCE_TRANSFORMER


class MultiModalQASystem:
    """다중 검색 모드 QA 시스템"""
    
    def __init__(self, use_vector: bool = True, verbose: bool = False):
        """
        Args:
            use_vector: 벡터 임베딩 모델 사용 여부
            verbose: 초기화 상세 로그
        """
        if verbose:
            print("="*80)
            print("조선왕조 GraphRAG 다중 검색 QA 시스템 초기화")
            print("="*80)
        
        # 1. LLM 설정
        if verbose:
            print("LLM 로드 중...")
        self.llm = Ollama(
            model=os.getenv("OLLAMA_MODEL", "exaone3.5:7.8b"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            request_timeout=int(os.getenv("REQUEST_TIMEOUT", "300")),
            temperature=0.3,
        )
        if verbose:
            print("LLM 로드 완료")
        
        # 2. 임베딩 모델 (선택적)
        self.embed_model = None
        self.use_vector = use_vector
        if use_vector:
            if verbose:
                print("임베딩 모델 로드 중...")
            try:
                self.embed_model = get_sentence_transformer()
                if verbose:
                    print("임베딩 모델 로드 완료")
            except Exception as e:
                print(f"[경고] 임베딩 모델 로드 실패: {e}")
                print("   벡터 검색 모드는 사용할 수 없습니다.")
                self.use_vector = False
        
        # 3. Neo4j 연결
        if verbose:
            print("Neo4j 연결 중...")
        self.driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI", "bolt://sungjun:7687"),
            auth=(
                os.getenv("NEO4J_USERNAME", "neo4j"),
                os.getenv("NEO4J_PASSWORD", "qqqqqqqq")
            )
        )
        self.database = os.getenv("NEO4J_DATABASE", "youngmin7")
        
        # 캐시 디렉토리 생성 (글로벌 검색용)
        self.cache_dir = Path("./cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.communities: List[Community] = []
        
        # 연결 테스트 및 스키마 정보 캐싱
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run("RETURN 1 as test")
                result.single()
            if verbose:
                print("Neo4j 연결 완료")
            
            # 그래프 스키마 정보 캐싱
            if verbose:
                print("그래프 스키마 조회 중...")
            self.relationship_types = self._get_relationship_types()
            self.node_labels = self._get_node_labels()
            if verbose:
                print(f"   관계 타입: {len(self.relationship_types)}개")
                print(f"   노드 라벨: {len(self.node_labels)}개")
        except Exception as e:
            print(f"[오류] Neo4j 연결 실패: {e}")
            raise
        
        if verbose:
            print("="*80)
            print("초기화 완료!")
            print("="*80 + "\n")
    
    # ========================================================================
    # 스키마 조회 메소드
    # ========================================================================
    
    def _get_relationship_types(self) -> List[str]:
        """그래프의 모든 관계 타입 조회"""
        with self.driver.session(database=self.database) as session:
            result = session.run("""
                CALL db.relationshipTypes() YIELD relationshipType
                RETURN relationshipType
                ORDER BY relationshipType
            """)
            return [record['relationshipType'] for record in result]
    
    def _get_node_labels(self) -> List[str]:
        """그래프의 모든 노드 라벨 조회"""
        with self.driver.session(database=self.database) as session:
            result = session.run("""
                CALL db.labels() YIELD label
                RETURN label
                ORDER BY label
            """)
            return [record['label'] for record in result]
    
    def _categorize_relationships(self, rel_types: List[str]) -> Dict[str, List[str]]:
        """관계 타입을 카테고리별로 분류"""
        categories = {
            '가족': [],
            '정치': [],
            '업적': [],
            '사건': [],
            '인물': [],
            '기타': []
        }
        
        family_keywords = ['아버지', '아들', '어머니', '왕비', '계비', '형제', '자녀']
        politics_keywords = ['즉위', '통치', '재위', '정치', '수렴청정', '경쟁', '영향']
        achievement_keywords = ['편찬', '저술', '주도', '실시', '명령', '설치', '확충', '건립', '제작']
        event_keywords = ['발생', '시대배경', '시기']
        person_keywords = ['등용', '정치인', '편찬자', '제작자', '사림', '세력']
        
        for rel in rel_types:
            categorized = False
            
            if any(kw in rel for kw in family_keywords):
                categories['가족'].append(rel)
                categorized = True
            elif any(kw in rel for kw in politics_keywords):
                categories['정치'].append(rel)
                categorized = True
            elif any(kw in rel for kw in achievement_keywords):
                categories['업적'].append(rel)
                categorized = True
            elif any(kw in rel for kw in event_keywords):
                categories['사건'].append(rel)
                categorized = True
            elif any(kw in rel for kw in person_keywords):
                categories['인물'].append(rel)
                categorized = True
            
            if not categorized:
                categories['기타'].append(rel)
        
        # 빈 카테고리 제거
        return {k: v for k, v in categories.items() if v}
    
    # ========================================================================
    # 1. 벡터 검색 모드
    # ========================================================================
    
    def vector_search(self, query: str, top_k: int = 10, search_nodes: bool = True, 
                     search_relationships: bool = True) -> Dict[str, Any]:
        """
        벡터 임베딩 기반 검색
        
        Args:
            query: 검색 질문
            top_k: 상위 k개 결과
            search_nodes: 노드 검색 여부
            search_relationships: 관계 검색 여부
        
        Returns:
            검색 결과 딕셔너리
        """
        if not self.embed_model:
            return {
                'error': '벡터 검색을 사용할 수 없습니다. 임베딩 모델이 로드되지 않았습니다.',
                'nodes': [],
                'relationships': []
            }
        
        # 질문을 벡터로 변환
        query_embedding = self.embed_model.encode(query, convert_to_numpy=True)
        
        results = {'nodes': [], 'relationships': []}
        
        with self.driver.session(database=self.database) as session:
            # 노드 검색
            if search_nodes:
                node_result = session.run("""
                    MATCH (n)
                    WHERE n.embedding IS NOT NULL
                    RETURN n.name as name, 
                           labels(n) as labels,
                           n.type as type,
                           n.category as category,
                           n.embedding as embedding,
                           n.embedding_text as text
                """)
                
                nodes = node_result.data()
                query_vec = query_embedding
                query_lower = query.lower()
                
                for node in nodes:
                    node_vec = np.array(node['embedding'])
                    similarity = np.dot(query_vec, node_vec) / (
                        np.linalg.norm(query_vec) * np.linalg.norm(node_vec) + 1e-10
                    )
                    
                    # 이름 직접 매칭 보너스
                    node_name_lower = node['name'].lower()
                    if query_lower == node_name_lower:
                        # 완전 일치: 점수 부스트
                        similarity = min(1.0, similarity * 1.5 + 0.3)
                    elif query_lower in node_name_lower or node_name_lower in query_lower:
                        # 부분 일치: 약간의 부스트
                        similarity = min(1.0, similarity * 1.2 + 0.1)
                    
                    results['nodes'].append({
                        'name': node['name'],
                        'labels': node['labels'],
                        'type': node.get('type'),
                        'category': node.get('category'),
                        'text': node.get('text', ''),
                        'score': float(similarity)
                    })
                
                results['nodes'].sort(key=lambda x: x['score'], reverse=True)
                results['nodes'] = results['nodes'][:top_k]
            
            # 관계 검색
            if search_relationships:
                rel_result = session.run("""
                    MATCH (source)-[r]->(target)
                    WHERE r.embedding IS NOT NULL
                    RETURN source.name as source_name,
                           type(r) as rel_type,
                           target.name as target_name,
                           r.embedding as embedding,
                           r.embedding_text as text
                """)
                
                rels = rel_result.data()
                
                for rel in rels:
                    rel_vec = np.array(rel['embedding'])
                    similarity = np.dot(query_vec, rel_vec) / (
                        np.linalg.norm(query_vec) * np.linalg.norm(rel_vec) + 1e-10
                    )
                    results['relationships'].append({
                        'source': rel['source_name'],
                        'type': rel['rel_type'],
                        'target': rel['target_name'],
                        'text': rel.get('text', ''),
                        'score': float(similarity)
                    })
                
                results['relationships'].sort(key=lambda x: x['score'], reverse=True)
                results['relationships'] = results['relationships'][:top_k]
        
        return results
    
    # ========================================================================
    # 2. 키워드 검색 모드
    # ========================================================================
    
    def keyword_search(self, query: str, top_k: int = 10) -> Dict[str, Any]:
        """
        키워드 매칭 기반 검색 (문자열 포함 검색)
        
        Args:
            query: 검색 질문
            top_k: 상위 k개 결과
        
        Returns:
            검색 결과 딕셔너리
        """
        # 키워드 변형 생성
        keywords = self._generate_keyword_variants(query)
        
        results = {'nodes': [], 'relationships': []}
        
        with self.driver.session(database=self.database) as session:
            # 노드 검색 (이름, 카테고리로)
            seen_nodes = set()
            for keyword in keywords[:5]:
                node_result = session.run("""
                    MATCH (n)
                    WHERE n.name CONTAINS $keyword 
                       OR n.category CONTAINS $keyword
                    RETURN DISTINCT n.name as name,
                           labels(n) as labels,
                           n.type as type,
                           n.category as category
                    LIMIT $limit
                """, keyword=keyword, limit=top_k)
                
                for record in node_result:
                    node_name = record['name']
                    if node_name not in seen_nodes:
                        seen_nodes.add(node_name)
                        # 매칭 품질에 따른 점수 계산
                        score = self._calculate_match_score(keyword, node_name, query)
                        results['nodes'].append({
                            'name': node_name,
                            'labels': record['labels'],
                            'type': record.get('type'),
                            'category': record.get('category'),
                            'score': score
                        })
            
            # 관계 검색 (관계 타입으로)
            seen_rels = set()
            for keyword in keywords[:3]:
                rel_result = session.run("""
                    MATCH (source)-[r]->(target)
                    WHERE type(r) CONTAINS $keyword
                       OR source.name CONTAINS $keyword
                       OR target.name CONTAINS $keyword
                    RETURN DISTINCT source.name as source_name,
                           type(r) as rel_type,
                           target.name as target_name
                    LIMIT $limit
                """, keyword=keyword, limit=top_k)
                
                for record in rel_result:
                    rel_key = f"{record['source_name']}-{record['rel_type']}-{record['target_name']}"
                    if rel_key not in seen_rels:
                        seen_rels.add(rel_key)
                        results['relationships'].append({
                            'source': record['source_name'],
                            'type': record['rel_type'],
                            'target': record['target_name'],
                            'score': 1.0 if keyword in record['rel_type'] else 0.7
                        })
            
            results['nodes'] = results['nodes'][:top_k]
            results['relationships'] = results['relationships'][:top_k]
        
        return results
    
    def _calculate_match_score(self, keyword: str, node_name: str, original_query: str) -> float:
        """매칭 품질에 따른 점수 계산"""
        node_name_lower = node_name.lower()
        keyword_lower = keyword.lower()
        
        # 1. 완전 일치: 1.0
        if node_name_lower == keyword_lower:
            return 1.0
        
        # 2. 노드명이 키워드로 시작: 0.9
        if node_name_lower.startswith(keyword_lower):
            return 0.9
        
        # 3. 키워드가 노드명에 포함되고, 키워드 길이가 긴 경우 (의미있는 매칭)
        if keyword_lower in node_name_lower:
            # 키워드 길이에 따라 점수 차등
            if len(keyword) >= 3:  # 3글자 이상
                # 키워드가 노드명에서 차지하는 비율
                ratio = len(keyword) / len(node_name)
                return 0.7 + (ratio * 0.2)  # 0.7 ~ 0.9
            else:  # 2글자 이하 (약한 매칭)
                return 0.5
        
        # 4. 기본값 (매칭되기는 했지만 약함)
        return 0.6
    
    def _generate_keyword_variants(self, query: str) -> List[str]:
        """키워드 변형 생성 (공백→언더스코어, 조사 제거 등)"""
        variants = []
        
        # 1. 원본
        variants.append(query)
        
        # 2. 공백 → 언더스코어
        variants.append(query.replace(' ', '_'))
        
        # 3. 공백 제거
        variants.append(query.replace(' ', ''))
        
        # 4. 단어 분리
        words = [w for w in query.split() if len(w) > 1]
        variants.extend(words)
        
        # 5. 조사 제거
        query_no_josa = query
        for josa in ['은', '는', '이', '가', '을', '를', '와', '과', '의', '에', '로', '에서', '?', '!']:
            query_no_josa = query_no_josa.replace(josa, '')
        
        if query_no_josa.strip() and query_no_josa != query:
            variants.append(query_no_josa.strip())
            variants.append(query_no_josa.replace(' ', '_').strip())
        
        # 중복 제거
        return [v for v in list(dict.fromkeys(variants)) if v.strip()]
    
    # ========================================================================
    # 3. Cypher 쿼리 모드
    # ========================================================================
    
    def cypher_search(self, query: str, auto_generate: bool = True, 
                     cypher_query: Optional[str] = None) -> Dict[str, Any]:
        """
        Cypher 쿼리 기반 검색
        
        Args:
            query: 자연어 질문
            auto_generate: LLM으로 Cypher 자동 생성 여부
            cypher_query: 직접 작성한 Cypher 쿼리 (auto_generate=False일 때)
        
        Returns:
            검색 결과 딕셔너리
        """
        if cypher_query is None and auto_generate:
            # LLM으로 Cypher 자동 생성
            cypher_query = self._generate_cypher(query)
        
        if not cypher_query:
            return {'error': 'Cypher 쿼리가 제공되지 않았습니다.', 'results': []}
        
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(cypher_query)
                records = result.data()
                
                return {
                    'cypher': cypher_query,
                    'results': records,
                    'count': len(records)
                }
        except Exception as e:
            return {
                'error': f'Cypher 쿼리 실행 실패: {str(e)}',
                'cypher': cypher_query,
                'results': []
            }
    
    def _generate_cypher(self, query: str) -> str:
        """LLM을 사용하여 자연어 질문을 Cypher 쿼리로 변환"""
        # 실제 그래프의 스키마 정보 사용
        categorized_rels = self._categorize_relationships(self.relationship_types)
        
        # 관계 타입을 카테고리별로 포맷팅
        rel_description = []
        for category, rels in categorized_rels.items():
            rel_list = ', '.join(rels[:10])  # 각 카테고리당 최대 10개
            if len(rels) > 10:
                rel_list += f" (외 {len(rels)-10}개)"
            rel_description.append(f"- {category}: {rel_list}")
        
        rel_text = '\n'.join(rel_description)
        
        # 모든 관계 타입 리스트 (LLM이 정확히 선택하도록)
        all_rels = ', '.join(self.relationship_types)
        
        # 질문에서 동사 추출 및 관계명 형식으로 변환 힌트
        verb_hints = self._extract_verb_hints(query)
        
        prompt = f"""당신은 Neo4j Cypher 쿼리 전문가입니다. 조선왕조 지식 그래프의 자연어 질문을 Cypher로 변환하세요.

[그래프 스키마]
노드 라벨:
{', '.join(self.node_labels)}

노드 속성:
- name: 개체명
- type: 타입
- category: 카테고리

관계 타입 (실제 그래프에서 조회됨, 언더스코어 주의!):
{rel_text}

[사용 가능한 모든 관계 타입]
{all_rels}

[질문 분석]
질문: {query}
{verb_hints}

[Cypher 쿼리 예시]
Q: 세종이 편찬한 책은?
A: MATCH (세종)-[:편찬함]->(book:Artifact) RETURN book.name LIMIT 10

Q: 태종에게 등용된 사람은?
A: MATCH (person)-[:등용됨]->(태종) RETURN person.name LIMIT 10

Q: 임진왜란이 발생한 시기는?
A: MATCH (임진왜란)-[:발생시기]->(date) RETURN date.name LIMIT 10

Q: 성종의 정치적 경쟁자는?
A: MATCH (성종)-[:정치적_경쟁자]-(competitor) RETURN competitor.name LIMIT 10

Q: 세조가 즉위한 사건은?
A: MATCH (세조)-[:즉위함]->(event) RETURN event.name LIMIT 10

[중요 규칙]
1. 질문의 키워드를 그대로 활용하되, 동사는 '~함' 또는 '~됨' 형태로 변환
   예: '편찬한' → ':편찬함', '등용된' → ':등용됨', '발생한' → ':발생시기' 또는 ':발생함'
2. 위의 [사용 가능한 모든 관계 타입]에서 질문에 가장 적합한 관계를 정확히 선택
3. 언더스코어가 포함된 관계는 반드시 언더스코어 포함 (예: 정치적_경쟁자, 재위기간_시작)
4. 개체명은 질문에 나온 한국어 그대로 사용
5. MATCH, WHERE, RETURN만 사용 (CREATE, DELETE 금지)
6. LIMIT 추가 (기본 10, 많은 결과 예상되면 20)
7. 관계 방향: 주어가 하는 행동은 (주어)-[:관계]->, 주어가 받는 행동은 (주어)<-[:관계]-
8. 양방향 관계는 (A)-[:관계]-(B)
9. 쿼리만 출력 (설명/주석 불필요)

Cypher 쿼리:"""
        
        try:
            response = self.llm.complete(prompt)
            cypher = response.text.strip()
            
            # 코드 블록 제거
            if '```' in cypher:
                cypher = cypher.split('```')[1]
                cypher = cypher.replace('cypher', '').replace('Cypher', '').strip()
            
            return cypher
        except Exception as e:
            print(f"[경고] Cypher 생성 실패: {e}")
            return ""
    
    def _extract_verb_hints(self, query: str) -> str:
        """질문에서 동사를 추출하고 관계명 형식으로 변환 힌트 제공"""
        # 일반적인 동사 패턴 매핑
        verb_patterns = {
            '편찬한': '편찬함',
            '편찬하': '편찬함',
            '저술한': '저술함',
            '저술하': '저술함',
            '주도한': '주도함',
            '주도하': '주도함',
            '실시한': '실시함',
            '실시하': '실시함',
            '설치한': '설치됨',
            '설치하': '설치됨',
            '등용된': '등용됨',
            '등용되': '등용됨',
            '발생한': '발생시기',
            '발생하': '발생시기',
            '일어난': '발생시기',
            '일어나': '발생시기',
            '즉위한': '즉위함',
            '즉위하': '즉위함',
            '통치한': '통치함',
            '통치하': '통치함',
            '명령한': '명령함',
            '명령하': '명령함',
            '건립한': '건립됨',
            '건립하': '건립됨',
            '제작한': '제작자',
            '제작하': '제작자',
            '확충한': '확충됨',
            '확충하': '확충됨',
        }
        
        # 질문에서 동사 찾기
        found_verbs = []
        for pattern, relation in verb_patterns.items():
            if pattern in query:
                # 실제 그래프에 해당 관계가 있는지 확인
                matching_rels = [r for r in self.relationship_types if relation in r]
                if matching_rels:
                    found_verbs.append(f"'{pattern}' → 관계: {', '.join(matching_rels)}")
        
        if found_verbs:
            return "힌트: " + " | ".join(found_verbs)
        return ""
    
    # ========================================================================
    # 4. 하이브리드 검색 모드
    # ========================================================================
    
    def hybrid_search(self, query: str, top_k: int = 15) -> Dict[str, Any]:
        """
        하이브리드 검색: 벡터 + 키워드 + 그래프 탐색
        
        Args:
            query: 검색 질문
            top_k: 상위 k개 결과
        
        Returns:
            통합 검색 결과
        """
        results = {
            'nodes': [],
            'relationships': [],
            'graph_context': None
        }
        
        # 1. 벡터 검색 (가능한 경우) - 가중치 0.4
        vector_weight = 0.4
        if self.embed_model:
            vector_results = self.vector_search(query, top_k=5, search_relationships=True)
            if 'error' not in vector_results:
                # 벡터 검색 결과에 가중치 적용
                for node in vector_results['nodes']:
                    node['score'] = node['score'] * vector_weight
                    node['source'] = 'vector'
                results['nodes'].extend(vector_results['nodes'])
                
                for rel in vector_results['relationships']:
                    rel['score'] = rel['score'] * vector_weight
                results['relationships'].extend(vector_results['relationships'])
        
        # 2. 키워드 검색 - 가중치 0.6 (더 신뢰성 있음)
        keyword_weight = 0.6
        keyword_results = self.keyword_search(query, top_k=5)
        # 키워드 검색 결과에 가중치 적용
        for node in keyword_results['nodes']:
            node['score'] = node['score'] * keyword_weight
            node['source'] = 'keyword'
        results['nodes'].extend(keyword_results['nodes'])
        
        for rel in keyword_results['relationships']:
            rel['score'] = rel['score'] * keyword_weight
        results['relationships'].extend(keyword_results['relationships'])
        
        # 3. 중복 제거 및 점수 병합
        seen_nodes = {}
        for node in results['nodes']:
            name = node['name']
            if name in seen_nodes:
                # 같은 노드가 여러 소스에서 나온 경우 점수 합산
                seen_nodes[name]['score'] = max(seen_nodes[name]['score'], node['score'])
            else:
                seen_nodes[name] = node
        
        # 점수 기준으로 정렬
        unique_nodes = sorted(seen_nodes.values(), key=lambda x: x['score'], reverse=True)
        results['nodes'] = unique_nodes[:top_k]
        
        seen_rels = set()
        unique_rels = []
        for rel in results['relationships']:
            rel_key = f"{rel['source']}-{rel['type']}-{rel['target']}"
            if rel_key not in seen_rels:
                seen_rels.add(rel_key)
                unique_rels.append(rel)
        results['relationships'] = unique_rels[:top_k]
        
        # 4. 그래프 탐색 (최상위 노드 기준)
        if results['nodes']:
            top_entity = results['nodes'][0]['name']
            results['graph_context'] = self._get_graph_context(top_entity)
        
        return results
    
    def _get_graph_context(self, entity_name: str, max_depth: int = 2) -> Optional[Dict[str, Any]]:
        """특정 개체 주변의 그래프 컨텍스트 조회"""
        with self.driver.session(database=self.database) as session:
            try:
                result = session.run("""
                    MATCH (center {name: $name})
                    OPTIONAL MATCH path = (center)-[r*1..2]-(neighbor)
                    WITH center, neighbor, r, length(path) as depth
                    WHERE neighbor IS NOT NULL
                    ORDER BY depth
                    LIMIT 30
                    RETURN 
                        center.name as center_name,
                        labels(center) as center_labels,
                        collect(DISTINCT {
                            name: neighbor.name,
                            labels: labels(neighbor),
                            relations: [rel in r | type(rel)],
                            depth: depth
                        }) as neighbors
                """, name=entity_name, max_depth=max_depth)
                
                data = result.data()
                return data[0] if data else None
            except Exception as e:
                print(f"[경고] 그래프 컨텍스트 조회 실패: {e}")
                return None
    
    # ========================================================================
    # 5. 글로벌 검색 모드 (Louvain 알고리즘)
    # ========================================================================
    
    def global_search(self, query: str, top_k: int = 5, use_cache: bool = True) -> Dict[str, Any]:
        """
        글로벌 검색: Louvain 알고리즘 기반 커뮤니티 탐지 + 계층적 요약
        
        Args:
            query: 검색 질문
            top_k: 상위 k개 커뮤니티 사용
            use_cache: 캐시 사용 여부
        
        Returns:
            검색 결과 딕셔너리
        """
        print(f"\n🔍 글로벌 검색 시작 (Louvain 알고리즘)")
        
        # 1. 커뮤니티 탐지 (캐시 확인)
        if not self.communities or not use_cache:
            self._detect_communities_louvain(use_cache=use_cache)
        
        # 2. 질문의 추상성 수준 판단
        target_level = self._determine_abstraction_level(query)
        print(f"   선택된 추상화 레벨: {target_level}")
        
        # 3. 해당 레벨의 커뮤니티 필터링
        level_communities = [
            comm for comm in self.communities 
            if comm.level == target_level
        ]
        
        if not level_communities:
            # 폴백: 레벨 0 사용
            print(f"   ⚠️ 레벨 {target_level} 커뮤니티가 없어 레벨 0 사용")
            level_communities = [
                comm for comm in self.communities 
                if comm.level == 0
            ]
        
        print(f"   선택된 커뮤니티 수: {len(level_communities)}개")
        
        # 4. 질문과 커뮤니티 요약 매칭 (벡터 유사도 또는 키워드)
        if self.embed_model:
            # 벡터 기반 매칭
            query_vec = self.embed_model.encode(query, convert_to_numpy=True)
            scored_communities = []
            
            for comm in level_communities:
                summary_vec = self.embed_model.encode(comm.summary, convert_to_numpy=True)
                similarity = np.dot(query_vec, summary_vec) / (
                    np.linalg.norm(query_vec) * np.linalg.norm(summary_vec) + 1e-10
                )
                scored_communities.append((comm, float(similarity)))
            
            scored_communities.sort(key=lambda x: x[1], reverse=True)
        else:
            # 키워드 기반 매칭 (폴백)
            query_lower = query.lower()
            scored_communities = []
            
            for comm in level_communities:
                summary_lower = comm.summary.lower()
                score = 0.0
                
                # 단순 키워드 매칭
                for word in query_lower.split():
                    if len(word) > 1 and word in summary_lower:
                        score += 1.0
                
                scored_communities.append((comm, score))
            
            scored_communities.sort(key=lambda x: x[1], reverse=True)
        
        # 5. 상위 k개 커뮤니티 선택
        top_communities = scored_communities[:top_k]
        
        print(f"   상위 {len(top_communities)}개 커뮤니티 선택됨")
        
        # 6. 결과 포맷팅
        results = {
            'communities': [],
            'abstraction_level': target_level
        }
        
        for comm, score in top_communities:
            results['communities'].append({
                'id': comm.id,
                'level': comm.level,
                'nodes': comm.nodes,
                'summary': comm.summary,
                'score': score,
                'node_count': len(comm.nodes)
            })
        
        return results
    
    def _detect_communities_louvain(self, use_cache: bool = True) -> None:
        """Louvain 알고리즘으로 커뮤니티 탐지 (캐시 지원)"""
        cache_file = self.cache_dir / "communities_louvain_hierarchical.pkl"
        
        # 캐시 로드
        if use_cache and cache_file.exists():
            print(f"   📦 캐시에서 커뮤니티 로드 중...")
            try:
                with open(cache_file, 'rb') as f:
                    cache_data = pickle.load(f)
                self.communities = cache_data['communities']
                print(f"   ✅ 캐시 로드 완료: {len(self.communities)}개 커뮤니티")
                print(f"      생성 시각: {cache_data.get('created_at', 'Unknown')}")
                return
            except Exception as e:
                print(f"   ⚠️ 캐시 로드 실패: {e}")
        
        # 새로 탐지
        print(f"   🔬 Louvain 알고리즘 실행 중... (2-3분 소요)")
        
        try:
            with self.driver.session(database=self.database) as session:
                # GDS 플러그인 확인
                try:
                    result = session.run("CALL gds.version() YIELD version RETURN version")
                    gds_version = result.single()
                    print(f"   ✅ Neo4j GDS 감지: {gds_version['version']}")
                except Exception as e:
                    print(f"   ❌ Neo4j GDS 플러그인이 설치되지 않았습니다.")
                    print(f"      에러: {e}")
                    print(f"   💡 폴백: 간단한 연결성 기반 커뮤니티 탐지로 전환")
                    self._detect_communities_fallback()
                    return
                
                # 그래프 프로젝션 확인 및 생성
                try:
                    result = session.run("""
                        CALL gds.graph.exists('joseon-graph') YIELD exists
                        RETURN exists
                    """)
                    graph_exists = result.single()['exists']
                    
                    if not graph_exists:
                        print("   📊 그래프 프로젝션 생성 중...")
                        session.run("""
                            CALL gds.graph.project(
                                'joseon-graph',
                                '*',
                                {
                                    REL: {
                                        type: '*',
                                        orientation: 'UNDIRECTED'
                                    }
                                }
                            )
                        """)
                except Exception as e:
                    print(f"   ⚠️ 그래프 프로젝션 실패: {e}")
                    print(f"   💡 폴백 모드로 전환")
                    self._detect_communities_fallback()
                    return
                
                # Louvain 실행 (계층적)
                result = session.run("""
                    CALL gds.louvain.stream('joseon-graph', {
                        includeIntermediateCommunities: true,
                        maxLevels: 10
                    })
                    YIELD nodeId, communityId, intermediateCommunityIds
                    RETURN gds.util.asNode(nodeId).name as name,
                           communityId,
                           intermediateCommunityIds
                """)
                
                records = result.data()
                print(f"   ✅ Louvain 완료: {len(records)}개 노드 분석됨")
        except Exception as e:
            print(f"   ❌ Louvain 실행 실패: {e}")
            print(f"   💡 폴백 모드로 전환")
            self._detect_communities_fallback()
            return
        
        # 커뮤니티 구축
        print(f"   🏗️ 계층적 커뮤니티 구축 중...")
        self.communities = self._build_hierarchical_communities(records)
        print(f"   ✅ 커뮤니티 구축 완료: {len(self.communities)}개")
        
        # 레벨별 통계
        level_counts = defaultdict(int)
        for comm in self.communities:
            level_counts[comm.level] += 1
        print(f"   📊 레벨별 분포: {dict(level_counts)}")
        
        # 캐시 저장
        if use_cache:
            try:
                cache_data = {
                    'communities': self.communities,
                    'algorithm': 'louvain',
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'total_communities': len(self.communities),
                    'levels': dict(level_counts)
                }
                with open(cache_file, 'wb') as f:
                    pickle.dump(cache_data, f)
                print(f"   💾 캐시 저장 완료: {cache_file}")
            except Exception as e:
                print(f"   ⚠️ 캐시 저장 실패: {e}")
    
    def _detect_communities_fallback(self) -> None:
        """GDS 없이 간단한 커뮤니티 탐지 (폴백)"""
        print(f"   🔄 간단한 연결성 기반 커뮤니티 탐지 시작...")
        
        with self.driver.session(database=self.database) as session:
            # 노드별 연결 정도 계산
            result = session.run("""
                MATCH (n)
                OPTIONAL MATCH (n)-[r]-(m)
                WITH n, count(DISTINCT m) as degree, collect(DISTINCT m.name) as neighbors
                RETURN n.name as name, 
                       labels(n) as labels,
                       degree,
                       neighbors[..10] as sample_neighbors
                ORDER BY degree DESC
            """)
            
            nodes_data = result.data()
            print(f"   ✅ {len(nodes_data)}개 노드 분석 완료")
            
            # 간단한 휴리스틱: 연결 정도로 그룹화
            # 상위 연결 노드들을 각각 커뮤니티 중심으로
            communities_dict = defaultdict(list)
            
            for i, node in enumerate(nodes_data[:50]):  # 상위 50개만
                # 간단한 그룹핑: 10개씩
                group_id = i // 10
                communities_dict[group_id].append(node['name'])
            
            # Community 객체 생성
            self.communities = []
            for comm_id, nodes in communities_dict.items():
                summary = self._generate_community_summary_simple(nodes, 0)
                self.communities.append(Community(
                    id=f"FALLBACK_C{comm_id}",
                    nodes=nodes,
                    summary=summary,
                    level=0
                ))
            
            print(f"   ✅ 폴백 커뮤니티 구축 완료: {len(self.communities)}개")
            print(f"   ⚠️ 참고: GDS 설치 시 더 정확한 커뮤니티 탐지 가능")
    
    def _build_hierarchical_communities(self, records: List[Dict]) -> List[Community]:
        """계층적 커뮤니티 구조 구축"""
        # 레벨별 커뮤니티 노드 수집
        level_communities = defaultdict(lambda: defaultdict(list))
        
        for record in records:
            node_name = record['name']
            intermediate_ids = record.get('intermediateCommunityIds', [])
            
            # 각 레벨별로 커뮤니티 ID 추적
            for level, comm_id in enumerate(intermediate_ids):
                level_communities[level][comm_id].append(node_name)
        
        # Community 객체 생성
        communities = []
        for level in sorted(level_communities.keys()):
            for comm_id, nodes in level_communities[level].items():
                # 요약 생성 (간단한 버전)
                summary = self._generate_community_summary_simple(nodes, level)
                
                communities.append(Community(
                    id=f"L{level}_C{comm_id}",
                    nodes=nodes,
                    summary=summary,
                    level=level
                ))
        
        return communities
    
    def _generate_community_summary_simple(self, nodes: List[str], level: int) -> str:
        """커뮤니티 간단 요약 생성 (LLM 호출 최소화)"""
        # 노드 샘플링 (최대 10개)
        sample_nodes = nodes[:10]
        nodes_str = ', '.join(sample_nodes)
        
        if len(nodes) > 10:
            nodes_str += f" 외 {len(nodes) - 10}개"
        
        # 레벨에 따른 간단한 설명
        if level == 0:
            return f"기본 커뮤니티: {nodes_str} ({len(nodes)}개 노드)"
        elif level == 1:
            return f"중간 커뮤니티: {nodes_str} ({len(nodes)}개 노드)"
        else:
            return f"상위 커뮤니티 (레벨 {level}): {nodes_str} ({len(nodes)}개 노드)"
    
    def _determine_abstraction_level(self, query: str) -> int:
        """질문의 추상성 수준 판단"""
        query_lower = query.lower()
        
        # 고수준 추상 키워드
        high_level_keywords = [
            '전반적', '전체적', '전반', '전체', '일반적', '대체로',
            '시대', '시기', '경향', '특징', '흐름', '변화', '발전',
            '조선', '왕조', '역사', '문화', '정치', '경제', '사회'
        ]
        
        # 중간 수준 키워드
        mid_level_keywords = [
            '왕', '시기', '대', '시절', '때', '동안', '기간',
            '정책', '제도', '사건', '업적'
        ]
        
        # 저수준 (구체적) 키워드
        low_level_keywords = [
            '누구', '무엇', '언제', '어디', '어떻게',
            '이름', '날짜', '장소', '인물', '구체적'
        ]
        
        # 점수 계산
        high_score = sum(1 for kw in high_level_keywords if kw in query_lower)
        mid_score = sum(1 for kw in mid_level_keywords if kw in query_lower)
        low_score = sum(1 for kw in low_level_keywords if kw in query_lower)
        
        # 질문 길이도 고려 (긴 질문 = 고수준)
        if len(query) > 50:
            high_score += 1
        elif len(query) < 20:
            low_score += 1
        
        # 레벨 결정
        if high_score > mid_score and high_score > low_score:
            return min(2, 2)  # 최대 레벨 2
        elif low_score > mid_score:
            return 0
        else:
            return 1
    
    # ========================================================================
    # 6. 답변 생성
    # ========================================================================
    
    def answer(self, query: str, mode: str = 'hybrid', verbose: bool = True, **kwargs) -> str:
        """
        질문에 답변
        
        Args:
            query: 사용자 질문
            mode: 검색 모드 ('vector', 'keyword', 'cypher', 'hybrid')
            verbose: 상세 로그 출력
            **kwargs: 모드별 추가 파라미터
        
        Returns:
            답변 텍스트
        """
        if verbose:
            print("\n" + "="*80)
            print(f"질문: {query}")
            print(f"검색 모드: {mode.upper()}")
            print("="*80)
        
        # 검색 실행
        if mode == 'vector':
            if verbose:
                print("\n[ 벡터 검색] 벡터 임베딩 검색 중...")
            search_results = self.vector_search(query, **kwargs)
        
        elif mode == 'keyword':
            if verbose:
                print("\n[ 키워드 검색] 키워드 매칭 검색 중...")
            search_results = self.keyword_search(query, **kwargs)
        
        elif mode == 'cypher':
            if verbose:
                print("\n[Cypher 검색] Cypher 쿼리 생성 및 실행 중...")
            search_results = self.cypher_search(query, **kwargs)
            
            # Cypher 모드는 결과 형식이 다름
            if verbose and 'cypher' in search_results:
                print(f"\n생성된 Cypher 쿼리:")
                print(f"  {search_results['cypher']}")
                print(f"\n결과: {search_results.get('count', 0)}개")
            
            if 'error' in search_results:
                return f"[오류] {search_results['error']}"
            
            # LLM으로 답변 생성
            return self._generate_answer_from_cypher(query, search_results, verbose)
        
        elif mode == 'hybrid':
            if verbose:
                print("\n[하이브리드 검색] 하이브리드 검색 중 (벡터 + 키워드 + 그래프)...")
            search_results = self.hybrid_search(query, **kwargs)
        
        elif mode == 'global':
            if verbose:
                print("\n[글로벌 검색] Louvain 기반 커뮤니티 검색 중...")
            search_results = self.global_search(query, **kwargs)
            
            # 글로벌 모드는 결과 형식이 다름
            if verbose:
                print(f"\n추상화 레벨: {search_results.get('abstraction_level', 'Unknown')}")
                print(f"매칭된 커뮤니티: {len(search_results.get('communities', []))}개")
            
            if 'error' in search_results:
                return f"[오류] {search_results['error']}"
            
            # LLM으로 답변 생성
            return self._generate_answer_from_global(query, search_results, verbose)
        
        else:
            return f"[오류] 지원하지 않는 모드입니다: {mode}"
        
        # 에러 처리
        if 'error' in search_results:
            return f"[오류] {search_results['error']}"
        
        # 결과 출력
        if verbose:
            self._print_search_results(search_results, mode)
        
        # LLM으로 답변 생성
        if verbose:
            print("\n[답변 생성] LLM 답변 생성 중...")
        
        answer = self._generate_answer(query, search_results, mode)
        
        if verbose:
            print("\n" + "="*80)
            print("답변:")
            print("="*80)
            print(answer)
            print("="*80 + "\n")
        
        return answer
    
    def _print_search_results(self, results: Dict[str, Any], mode: str):
        """검색 결과 출력"""
        print("\n" + "-"*80)
        print("검색 결과:")
        print("-"*80)
        
        # 노드 결과
        if 'nodes' in results and results['nodes']:
            print(f"\n[노드] {len(results['nodes'])}개:")
            for i, node in enumerate(results['nodes'][:5], 1):
                label = node.get('labels', ['Unknown'])[0] if isinstance(node.get('labels'), list) else 'Unknown'
                score = node.get('score', 0)
                print(f"  {i}. {node['name']} ({label}) - 점수: {score:.3f}")
        
        # 관계 결과
        if 'relationships' in results and results['relationships']:
            print(f"\n[관계] {len(results['relationships'])}개:")
            for i, rel in enumerate(results['relationships'][:5], 1):
                score = rel.get('score', 0)
                print(f"  {i}. {rel['source']} --[{rel['type']}]--> {rel['target']} - 점수: {score:.3f}")
        
        # 그래프 컨텍스트
        if 'graph_context' in results and results['graph_context']:
            gc = results['graph_context']
            neighbors = gc.get('neighbors', [])
            print(f"\n[그래프] '{gc['center_name']}' 주변 개체 {len(neighbors)}개")
        
        # 커뮤니티 결과 (글로벌 검색 전용)
        if mode == 'global' and 'communities' in results and results['communities']:
            print(f"\n[커뮤니티] {len(results['communities'])}개:")
            for i, comm in enumerate(results['communities'], 1):
                print(f"  {i}. {comm['id']} (레벨 {comm['level']}) - 점수: {comm['score']:.3f}")
                print(f"     노드 {comm['node_count']}개")
    
    def _generate_answer(self, query: str, results: Dict[str, Any], mode: str) -> str:
        """검색 결과를 바탕으로 LLM 답변 생성"""
        context = self._format_context(results, mode)
        
        prompt = f"""당신은 조선왕조 역사 전문가입니다. 지식 그래프 검색 결과를 바탕으로 질문에 답변하세요.

[검색 결과]
{context}

[질문]
{query}

[답변 규칙]
1. 검색 결과에서 제공된 정보만 사용
2. 간결하고 명확하게 2-4문장으로 답변
3. 근거가 되는 개체나 관계를 명시
4. 정보가 부족하면 "검색된 정보로는 정확한 답변이 어렵습니다"라고 답변
5. 한국어로 답변

답변:"""
        
        try:
            response = self.llm.complete(prompt)
            return response.text.strip()
        except Exception as e:
            return f"[오류] LLM 답변 생성 실패: {e}"
    
    def _generate_answer_from_cypher(self, query: str, results: Dict[str, Any], verbose: bool) -> str:
        """Cypher 쿼리 결과를 바탕으로 답변 생성"""
        cypher = results.get('cypher', '')
        data = results.get('results', [])
        
        if not data:
            return "검색 결과가 없습니다. Cypher 쿼리가 잘못되었거나 해당 데이터가 그래프에 없을 수 있습니다."
        
        # 결과를 보기 좋게 포맷팅
        if verbose:
            print("\n[결과] Cypher 쿼리 결과:")
            print("-" * 80)
            for i, record in enumerate(data[:10], 1):
                print(f"{i}. {record}")
            print()
        
        # 결과를 텍스트로 변환
        context_lines = []
        for i, record in enumerate(data[:10], 1):
            context_lines.append(f"{i}. {record}")
        context = '\n'.join(context_lines)
        
        prompt = f"""조선왕조 지식 그래프에서 다음 Cypher 쿼리를 실행한 결과입니다.

[Cypher 쿼리]
{cypher}

[쿼리 결과]
{context}

[질문]
{query}

위 결과를 바탕으로 질문에 2-3문장으로 답변하세요.

답변:"""
        
        try:
            response = self.llm.complete(prompt)
            return response.text.strip()
        except Exception as e:
            return f"[오류] 답변 생성 실패: {e}"
    
    def _generate_answer_from_global(self, query: str, results: Dict[str, Any], verbose: bool) -> str:
        """글로벌 검색 결과를 바탕으로 답변 생성"""
        communities = results.get('communities', [])
        abstraction_level = results.get('abstraction_level', 0)
        
        if not communities:
            return "검색 결과가 없습니다. 커뮤니티 탐지가 실패했거나 해당 내용과 관련된 커뮤니티가 없을 수 있습니다."
        
        # 결과를 보기 좋게 포맷팅
        if verbose:
            print("\n[결과] 글로벌 검색 결과:")
            print("-" * 80)
            for i, comm in enumerate(communities[:5], 1):
                print(f"{i}. [커뮤니티 {comm['id']}] (레벨 {comm['level']}, 노드 {comm['node_count']}개)")
                print(f"   점수: {comm['score']:.3f}")
                print(f"   요약: {comm['summary'][:100]}...")
            print()
        
        # 컨텍스트 생성
        context_lines = []
        for i, comm in enumerate(communities[:3], 1):  # 상위 3개만 사용
            context_lines.append(f"[커뮤니티 {i}]")
            context_lines.append(f"노드 수: {comm['node_count']}개")
            context_lines.append(f"요약: {comm['summary']}")
            context_lines.append(f"주요 노드: {', '.join(comm['nodes'][:10])}")
            context_lines.append("")
        
        context = '\n'.join(context_lines)
        
        prompt = f"""당신은 조선왕조 역사 전문가입니다. 지식 그래프의 커뮤니티 분석 결과를 바탕으로 질문에 답변하세요.

[커뮤니티 분석 결과]
추상화 레벨: {abstraction_level}
{context}

[질문]
{query}

[답변 규칙]
1. 커뮤니티 분석 결과에서 제공된 정보만 사용
2. 2-4문장으로 간결하게 답변
3. 큰 그림과 맥락을 제공
4. 정보가 부족하면 "제공된 커뮤니티 정보로는 정확한 답변이 어렵습니다"라고 답변
5. 한국어로 답변

답변:"""
        
        try:
            response = self.llm.complete(prompt)
            return response.text.strip()
        except Exception as e:
            return f"[오류] 답변 생성 실패: {e}"
    
    def _format_context(self, results: Dict[str, Any], mode: str) -> str:
        """검색 결과를 텍스트로 포맷팅"""
        lines = []
        
        # 노드 결과
        if 'nodes' in results and results['nodes']:
            lines.append("[관련 개체]")
            for i, node in enumerate(results['nodes'][:5], 1):
                label = node.get('labels', ['Unknown'])[0] if isinstance(node.get('labels'), list) else 'Unknown'
                score = node.get('score', 0)
                lines.append(f"  {i}. {node['name']} ({label}) - 유사도: {score:.3f}")
                
                if 'text' in node and node['text']:
                    lines.append(f"     정보: {node['text'][:100]}...")
        
        # 관계 결과
        if 'relationships' in results and results['relationships']:
            lines.append("\n[관련 관계]")
            for i, rel in enumerate(results['relationships'][:5], 1):
                score = rel.get('score', 0)
                lines.append(f"  {i}. {rel['source']} --[{rel['type']}]--> {rel['target']} - 유사도: {score:.3f}")
                
                if 'text' in rel and rel['text']:
                    lines.append(f"     설명: {rel['text'][:100]}...")
        
        # 그래프 컨텍스트
        if 'graph_context' in results and results['graph_context']:
            gc = results['graph_context']
            lines.append(f"\n[그래프 탐색] '{gc['center_name']}' 주변 관계:")
            
            neighbors = gc.get('neighbors', [])[:5]
            for neighbor in neighbors:
                relations = neighbor.get('relations', [])
                rel_str = ', '.join(set(relations[:3])) if relations else '연결됨'
                lines.append(f"  - {neighbor['name']}: {rel_str}")
        
        return '\n'.join(lines) if lines else "검색 결과가 없습니다."
    
    def close(self):
        """리소스 정리"""
        if self.driver:
            self.driver.close()


# ============================================================================
# CLI 인터페이스
# ============================================================================

def interactive_mode(qa_system: MultiModalQASystem, default_mode: str = 'hybrid'):
    """대화형 모드"""
    print("\n" + "="*80)
    print("조선왕조 GraphRAG 다중 검색 QA 시스템")
    print("="*80)
    print("\n사용 가능한 검색 모드:")
    print("  • vector   - 벡터 임베딩 기반 유사도 검색")
    print("  • keyword  - 키워드 매칭 기반 검색")
    print("  • cypher   - Cypher 쿼리 기반 검색 (Text-to-Cypher)")
    print("  • global   - 글로벌 검색 (Louvain 커뮤니티 탐지)")
    print("  • hybrid   - 하이브리드 (벡터 + 키워드 + 그래프 탐색)")
    print("\n명령어:")
    print("  • /mode <모드>  - 검색 모드 변경")
    print("  • /help         - 도움말")
    print("  • /exit         - 종료")
    print("="*80 + "\n")
    
    current_mode = default_mode
    
    try:
        while True:
            try:
                query = input(f"\n💬 질문 ({current_mode}): ").strip()
                
                if not query:
                    continue
                
                # 명령어 처리
                if query.startswith('/'):
                    cmd_parts = query[1:].lower().split()
                    cmd = cmd_parts[0]
                    
                    if cmd == 'exit' or cmd == 'quit':
                        print("\n시스템을 종료합니다.")
                        break
                    
                    elif cmd == 'mode' and len(cmd_parts) > 1:
                        new_mode = cmd_parts[1]
                        if new_mode in ['vector', 'keyword', 'cypher', 'global', 'hybrid']:
                            current_mode = new_mode
                            print(f"검색 모드 변경: {current_mode.upper()}")
                        else:
                            print(f"[오류] 지원하지 않는 모드입니다: {new_mode}")
                            print("   사용 가능: vector, keyword, cypher, global, hybrid")
                    
                    elif cmd == 'help':
                        print("\n" + "="*60)
                        print("검색 모드 설명")
                        print("="*60)
                        print("\n  vector:")
                        print("    - 질문과 노드/관계의 임베딩 유사도로 검색")
                        print("    - 의미 기반 검색, 동의어/유사 표현 이해")
                        print("    - 예: '효종의 아버지', '세종의 업적'")
                        print("\n  keyword:")
                        print("    - 질문에서 키워드 추출하여 문자열 매칭")
                        print("    - 정확한 개체명/관계명 검색")
                        print("    - 예: '태종', '정치적 경쟁자'")
                        print("\n  cypher:")
                        print("    - LLM이 질문을 Cypher 쿼리로 변환")
                        print("    - 복잡한 패턴 검색, 정확한 답변")
                        print("    - 예: '세종의 아버지의 업적'")
                        print("\n  global:")
                        print("    - Louvain 알고리즘 기반 커뮤니티 탐지")
                        print("    - 계층적 구조 분석, 큰 그림 파악")
                        print("    - 예: '조선 초기의 전반적인 정치 상황'")
                        print("\n  hybrid:")
                        print("    - 벡터 + 키워드 + 그래프 탐색 통합")
                        print("    - 가장 높은 정확도, 모든 질문 대응")
                        print("    - 예: 모든 유형의 질문")
                        print("="*60)
                    
                    continue
                
                # 질문 처리
                qa_system.answer(query, mode=current_mode, verbose=True)
            
            except KeyboardInterrupt:
                print("\n\nCtrl+C 감지 - 시스템을 종료합니다.")
                break
            
            except Exception as e:
                print(f"\n[오류] 오류 발생: {e}")
    
    finally:
        qa_system.close()


def batch_mode(qa_system: MultiModalQASystem, questions: List[str], mode: str = 'hybrid'):
    """배치 모드 - 여러 질문 자동 처리"""
    print("\n" + "="*80)
    print(f"배치 모드 실행 ({mode.upper()})")
    print("="*80)
    
    for i, question in enumerate(questions, 1):
        print(f"\n[{i}/{len(questions)}]")
        qa_system.answer(question, mode=mode, verbose=True)
        print("\n" + "-"*80)
    
    qa_system.close()


def single_question_mode(qa_system: MultiModalQASystem, question: str, mode: str = 'hybrid'):
    """단일 질문 모드"""
    answer = qa_system.answer(question, mode=mode, verbose=True)
    qa_system.close()
    return answer


def main():
    """메인 함수 - CLI 파싱"""
    parser = argparse.ArgumentParser(
        description='조선왕조 GraphRAG 다중 검색 QA 시스템',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 대화형 모드 (기본)
  python qa_multimodal.py
  
  # 특정 모드로 대화형 시작
  python qa_multimodal.py -m vector
  
  # 단일 질문
  python qa_multimodal.py -q "세종" -m vector
  
  # 배치 모드
  python qa_multimodal.py --batch questions.txt -m cypher
  
  # 벡터 모델 없이 실행 (키워드/Cypher만)
  python qa_multimodal.py --no-vector
        """
    )
    
    parser.add_argument('-m', '--mode', 
                       choices=['vector', 'keyword', 'cypher', 'global', 'hybrid'],
                       default='hybrid',
                       help='검색 모드 (기본: hybrid)')
    
    parser.add_argument('-q', '--question',
                       type=str,
                       help='단일 질문')
    
    parser.add_argument('--batch',
                       type=str,
                       help='배치 모드: 질문 파일 경로 (한 줄에 하나씩)')
    
    parser.add_argument('--no-vector',
                       action='store_true',
                       help='벡터 임베딩 모델 로드 안 함')
    
    parser.add_argument('-v', '--verbose',
                       action='store_true',
                       help='상세 초기화 로그 출력')
    
    args = parser.parse_args()
    
    # QA 시스템 초기화
    try:
        qa_system = MultiModalQASystem(
            use_vector=not args.no_vector,
            verbose=args.verbose
        )
    except Exception as e:
        print(f"[오류] 시스템 초기화 실패: {e}")
        return 1
    
    # 실행 모드 선택
    if args.question:
        # 단일 질문 모드
        single_question_mode(qa_system, args.question, args.mode)
    
    elif args.batch:
        # 배치 모드
        try:
            with open(args.batch, 'r', encoding='utf-8') as f:
                questions = [line.strip() for line in f if line.strip()]
            batch_mode(qa_system, questions, args.mode)
        except FileNotFoundError:
            print(f"[오류] 파일을 찾을 수 없습니다: {args.batch}")
            qa_system.close()
            return 1
    
    else:
        # 대화형 모드 (기본)
        interactive_mode(qa_system, args.mode)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
