"""
전체 input 폴더 파일을 일괄 처리하여 통합 그래프 구축
"""
import os
from pathlib import Path
from graph_builder import build_graph
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()


def batch_process_all_files():
    """input 폴더의 모든 txt 파일 일괄 처리"""
    
    input_dir = Path("input")
    txt_files = sorted(input_dir.glob("*.txt"))
    
    if not txt_files:
        print("❌ input 폴더에 txt 파일이 없습니다!")
        return
    
    print("="*80)
    print(f"🚀 조선왕조 26대 왕 일괄 처리: {len(txt_files)}개 파일")
    print("="*80)
    
    results = []
    
    # 진행률 표시
    for i, file_path in enumerate(tqdm(txt_files, desc="전체 진행")):
        print(f"\n{'='*80}")
        print(f"📖 [{i+1}/{len(txt_files)}] {file_path.name} 처리 중...")
        print(f"{'='*80}")
        
        try:
            # 첫 번째 파일만 DB 초기화, 나머지는 추가
            clear_db = (i == 0)
            result = build_graph(str(file_path), clear_db=clear_db)
            results.append(result)
            print(f"✓ {file_path.name} 완료: {result['entities']}개 개체, {result['relations']}개 관계")
            
        except Exception as e:
            print(f"⚠️  {file_path.name} 처리 실패: {e}")
            results.append({
                "file": str(file_path),
                "error": str(e)
            })
    
    # 최종 통계
    print("\n" + "="*80)
    print("📊 일괄 처리 완료 - 최종 통계")
    print("="*80)
    
    total_entities = sum(r.get('entities', 0) for r in results)
    total_relations = sum(r.get('relations', 0) for r in results)
    success_count = sum(1 for r in results if 'error' not in r)
    
    print(f"\n✓ 성공: {success_count}/{len(txt_files)} 파일")
    print(f"  총 추출된 개체: {total_entities:,}개")
    print(f"  총 추출된 관계: {total_relations:,}개")
    
    if success_count < len(txt_files):
        print(f"\n⚠️  실패: {len(txt_files) - success_count}개 파일")
        for r in results:
            if 'error' in r:
                print(f"  - {Path(r['file']).name}: {r['error']}")
    
    print("\n✅ 조선왕조 통합 지식 그래프 구축 완료!")
    print("Neo4j Browser: http://localhost:7474")
    print("\n추천 쿼리:")
    print("  # 전체 그래프 구조")
    print("  MATCH p=()-[r]->() RETURN p LIMIT 100")
    print("  ")
    print("  # 왕들 중심 네트워크")
    print("  MATCH (n:Entity) WHERE n.type = 'Person' RETURN n")
    print("  ")
    print("  # 특정 왕 중심 서브그래프")
    print("  MATCH p=(n:Entity {name: '세종'})-[*1..2]-() RETURN p")


if __name__ == "__main__":
    batch_process_all_files()
