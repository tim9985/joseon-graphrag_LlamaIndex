"""
조선왕조 GraphRAG Flask API 서버
React 프론트엔드와 연동
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys
from dotenv import load_dotenv

# qa_multimodal.py의 MultiModalQASystem 임포트
from qa_multimodal import MultiModalQASystem

load_dotenv()

app = Flask(__name__)
CORS(app)  # CORS 허용

# QA 시스템 초기화 (서버 시작 시 한 번만)
print("="*80)
print("조선왕조 GraphRAG API 서버 초기화 중...")
print("="*80)

try:
    qa_system = MultiModalQASystem(
        use_vector=True,  # 벡터 검색 사용
        verbose=True      # 초기화 로그 출력
    )
    print("\n✅ QA 시스템 초기화 완료!")
except Exception as e:
    print(f"\n❌ QA 시스템 초기화 실패: {e}")
    sys.exit(1)


@app.route('/api/ask', methods=['POST'])
def ask():
    """
    질문 답변 API
    
    Request Body:
        {
            "question": "세종의 아버지는?",
            "mode": "hybrid"  // optional: vector, keyword, cypher, global, hybrid (기본값: hybrid)
        }
    
    Response:
        {
            "answer": "세종의 아버지는 태종입니다...",
            "graphData": {
                "nodes": [...],
                "relationships": [...]
            },
            "searchResults": {...},  // 검색 결과 상세 정보
            "mode": "hybrid"
        }
    """
    try:
        data = request.get_json()
        
        if not data or 'question' not in data:
            return jsonify({'error': '질문이 제공되지 않았습니다.'}), 400
        
        question = data['question'].strip()
        mode = data.get('mode', 'hybrid')  # 기본값: hybrid
        
        if not question:
            return jsonify({'error': '질문이 비어 있습니다.'}), 400
        
        # 지원하는 모드 확인
        supported_modes = ['vector', 'keyword', 'cypher', 'global', 'hybrid']
        if mode not in supported_modes:
            return jsonify({'error': f'지원하지 않는 모드입니다: {mode}'}), 400
        
        print(f"\n{'='*80}")
        print(f"[API] 질문: {question}")
        print(f"[API] 모드: {mode}")
        print(f"{'='*80}")
        
        # 검색 실행
        search_results = None
        
        if mode == 'vector':
            search_results = qa_system.vector_search(question, top_k=10)
        elif mode == 'keyword':
            search_results = qa_system.keyword_search(question, top_k=10)
        elif mode == 'cypher':
            search_results = qa_system.cypher_search(question, auto_generate=True)
        elif mode == 'global':
            search_results = qa_system.global_search(question, top_k=5, use_cache=True)
        elif mode == 'hybrid':
            search_results = qa_system.hybrid_search(question, top_k=15)
        
        # 에러 체크
        if 'error' in search_results:
            return jsonify({
                'error': search_results['error'],
                'answer': f"검색 중 오류가 발생했습니다: {search_results['error']}",
                'graphData': {'nodes': [], 'relationships': []},
                'mode': mode
            }), 500
        
        # 답변 생성
        answer = qa_system._generate_answer(question, search_results, mode)
        
        # 그래프 데이터 변환 (React Flow 형식에 맞게)
        graph_data = _convert_to_graph_data(search_results, mode)
        
        print(f"\n[API] 답변 생성 완료")
        print(f"[API] 노드: {len(graph_data['nodes'])}개, 관계: {len(graph_data['relationships'])}개")
        print(f"{'='*80}\n")
        
        return jsonify({
            'answer': answer,
            'graphData': graph_data,
            'searchResults': _serialize_search_results(search_results),
            'mode': mode,
            'success': True
        })
    
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"\n[API 오류] {e}")
        print(error_detail)
        
        return jsonify({
            'error': str(e),
            'answer': f'서버 오류가 발생했습니다: {str(e)}',
            'graphData': {'nodes': [], 'relationships': []},
            'mode': mode if 'mode' in locals() else 'unknown'
        }), 500


@app.route('/api/health', methods=['GET'])
def health():
    """헬스 체크 엔드포인트"""
    return jsonify({
        'status': 'ok',
        'service': 'joseon-graphrag-api',
        'qa_system': 'initialized'
    })


@app.route('/api/modes', methods=['GET'])
def get_modes():
    """사용 가능한 검색 모드 목록"""
    return jsonify({
        'modes': [
            {
                'id': 'vector',
                'name': '벡터 검색',
                'description': '임베딩 유사도 기반 검색 (의미적 유사성)'
            },
            {
                'id': 'keyword',
                'name': '키워드 검색',
                'description': '키워드 매칭 기반 검색 (정확한 매칭)'
            },
            {
                'id': 'cypher',
                'name': 'Cypher 검색',
                'description': 'LLM이 Cypher 쿼리로 변환하여 검색'
            },
            {
                'id': 'hybrid',
                'name': '하이브리드 검색',
                'description': '벡터 + 키워드 + 그래프 탐색 통합 (권장)'
            }
        ]
    })


def _convert_to_graph_data(search_results, mode):
    """
    QA 시스템의 검색 결과를 React Flow 그래프 데이터로 변환
    
    Returns:
        {
            "nodes": [
                {
                    "id": "node_id",
                    "labels": ["Person"],
                    "properties": {"name": "세종"}
                }
            ],
            "relationships": [
                {
                    "id": "rel_id",
                    "type": "아버지",
                    "start": "node_1",
                    "end": "node_2"
                }
            ]
        }
    """
    nodes = []
    relationships = []
    node_map = {}  # name -> node_id 매핑
    node_counter = 0
    rel_counter = 0
    
    # Cypher 모드는 결과 형식이 다름
    if mode == 'cypher':
        cypher_results = search_results.get('results', [])
        
        # Cypher 결과를 노드로 변환 (결과가 단순 값일 수 있음)
        for result in cypher_results[:20]:  # 최대 20개
            for key, value in result.items():
                if value and isinstance(value, str):
                    node_id = f"node_{node_counter}"
                    node_counter += 1
                    
                    nodes.append({
                        'id': node_id,
                        'labels': ['Result'],
                        'properties': {
                            'name': value,
                            'key': key
                        }
                    })
        
        return {'nodes': nodes, 'relationships': relationships}
    
    # 노드 변환
    if 'nodes' in search_results:
        for node in search_results['nodes'][:15]:  # 최대 15개 노드
            node_name = node.get('name', 'Unknown')
            
            if node_name not in node_map:
                node_id = f"node_{node_counter}"
                node_counter += 1
                node_map[node_name] = node_id
                
                nodes.append({
                    'id': node_id,
                    'labels': node.get('labels', ['Unknown']),
                    'properties': {
                        'name': node_name,
                        'type': node.get('type'),
                        'category': node.get('category'),
                        'score': node.get('score', 0)
                    }
                })
    
    # 관계 변환
    if 'relationships' in search_results:
        for rel in search_results['relationships'][:20]:  # 최대 20개 관계
            source_name = rel.get('source')
            target_name = rel.get('target')
            rel_type = rel.get('type', 'RELATED_TO')
            
            # 소스/타겟 노드가 없으면 추가
            if source_name and source_name not in node_map:
                node_id = f"node_{node_counter}"
                node_counter += 1
                node_map[source_name] = node_id
                nodes.append({
                    'id': node_id,
                    'labels': ['Entity'],
                    'properties': {'name': source_name}
                })
            
            if target_name and target_name not in node_map:
                node_id = f"node_{node_counter}"
                node_counter += 1
                node_map[target_name] = node_id
                nodes.append({
                    'id': node_id,
                    'labels': ['Entity'],
                    'properties': {'name': target_name}
                })
            
            # 관계 추가
            if source_name and target_name:
                relationships.append({
                    'id': f"rel_{rel_counter}",
                    'type': rel_type,
                    'start': node_map[source_name],
                    'end': node_map[target_name],
                    'properties': {
                        'score': rel.get('score', 0)
                    }
                })
                rel_counter += 1
    
    # 그래프 컨텍스트 추가 (hybrid 모드)
    if 'graph_context' in search_results and search_results['graph_context']:
        gc = search_results['graph_context']
        center_name = gc.get('center_name')
        
        if center_name and center_name not in node_map:
            node_id = f"node_{node_counter}"
            node_counter += 1
            node_map[center_name] = node_id
            nodes.append({
                'id': node_id,
                'labels': gc.get('center_labels', ['Unknown']),
                'properties': {'name': center_name}
            })
        
        # 이웃 노드 추가
        for neighbor in gc.get('neighbors', [])[:10]:
            neighbor_name = neighbor.get('name')
            
            if neighbor_name and neighbor_name not in node_map:
                node_id = f"node_{node_counter}"
                node_counter += 1
                node_map[neighbor_name] = node_id
                nodes.append({
                    'id': node_id,
                    'labels': neighbor.get('labels', ['Unknown']),
                    'properties': {'name': neighbor_name}
                })
            
            # 중심 노드와의 관계 추가
            if center_name and neighbor_name:
                rel_types = neighbor.get('relations', [])
                rel_type = rel_types[0] if rel_types else 'CONNECTED_TO'
                
                relationships.append({
                    'id': f"rel_{rel_counter}",
                    'type': rel_type,
                    'start': node_map[center_name],
                    'end': node_map[neighbor_name],
                    'properties': {
                        'depth': neighbor.get('depth', 1)
                    }
                })
                rel_counter += 1
    
    return {'nodes': nodes, 'relationships': relationships}


def _serialize_search_results(results):
    """검색 결과를 JSON 직렬화 가능하도록 변환"""
    # numpy 타입 등을 Python 네이티브 타입으로 변환
    import json
    
    def convert_value(obj):
        if hasattr(obj, 'tolist'):  # numpy array
            return obj.tolist()
        if hasattr(obj, 'item'):  # numpy scalar
            return obj.item()
        return obj
    
    # 딕셔너리를 재귀적으로 변환
    def recursive_convert(data):
        if isinstance(data, dict):
            return {k: recursive_convert(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [recursive_convert(item) for item in data]
        else:
            return convert_value(data)
    
    return recursive_convert(results)


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    
    print("\n" + "="*80)
    print(f"🚀 조선왕조 GraphRAG API 서버 시작")
    print(f"   포트: {port}")
    print(f"   엔드포인트: http://localhost:{port}/api/ask")
    print(f"   헬스체크: http://localhost:{port}/api/health")
    print("="*80 + "\n")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False  # 프로덕션에서는 False
    )
