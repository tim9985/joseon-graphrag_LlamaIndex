import React, { useState, useEffect, useRef } from 'react'
import mermaid from 'mermaid'
import './App.css'

// Mermaid 초기화
mermaid.initialize({
  startOnLoad: true,
  theme: 'dark',
  themeVariables: {
    primaryColor: '#0052a3',
    primaryTextColor: '#e5e7eb',
    primaryBorderColor: '#0052a3',
    lineColor: '#f5b700',
    secondaryColor: '#bf1e33',
    tertiaryColor: '#020617',
  },
  flowchart: {
    curve: 'basis',
    padding: 20,
  },
})

interface GraphData {
  nodes: Array<{
    id: string
    labels: string[]
    properties: {
      name: string
      type?: string
      category?: string
      score?: number
    }
  }>
  relationships: Array<{
    id: string
    type: string
    start: string
    end: string
    properties?: any
  }>
}

function App() {
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState<string | null>(null)
  const [mode, setMode] = useState<'vector' | 'keyword' | 'cypher' | 'global' | 'hybrid'>('hybrid')
  const [isLoading, setIsLoading] = useState(false)
  const [graphData, setGraphData] = useState<GraphData | null>(null)
  const [zoom, setZoom] = useState(1)
  const mermaidRef = useRef<HTMLDivElement>(null)
  const graphContainerRef = useRef<HTMLDivElement>(null)

  // Mermaid 그래프 렌더링
  useEffect(() => {
    if (graphData && graphData.nodes.length > 0 && mermaidRef.current) {
      const mermaidCode = generateMermaidCode(graphData)
      
      // 기존 내용 제거
      mermaidRef.current.innerHTML = ''
      
      // 새로운 div 생성
      const div = document.createElement('div')
      div.className = 'mermaid'
      div.textContent = mermaidCode
      mermaidRef.current.appendChild(div)
      
      // Mermaid 렌더링
      mermaid.contentLoaded()
      
      // 줌 리셋
      setZoom(1)
    }
  }, [graphData])

  // 마우스 휠로 줌
  useEffect(() => {
    const handleWheel = (e: WheelEvent) => {
      if (e.ctrlKey || e.metaKey) {
        e.preventDefault()
        const delta = e.deltaY > 0 ? -0.1 : 0.1
        setZoom((prev) => Math.min(Math.max(prev + delta, 0.5), 3))
      }
    }

    const container = graphContainerRef.current
    if (container) {
      container.addEventListener('wheel', handleWheel, { passive: false })
    }

    return () => {
      if (container) {
        container.removeEventListener('wheel', handleWheel)
      }
    }
  }, [])

  const generateMermaidCode = (data: GraphData): string => {
    let code = 'graph LR\n'
    
    const nodeMap = new Map<string, string>()
    
    // 노드 정의
    data.nodes.forEach((node, index) => {
      const nodeId = `N${index}`
      nodeMap.set(node.id, nodeId)
      
      const name = node.properties.name || 'Unknown'
      const label = node.labels?.[0] || 'Unknown'
      
      code += `    ${nodeId}["${name}<br/>(${label})"]\n`
    })
    
    code += '\n'
    
    // 관계 정의
    data.relationships.forEach((rel) => {
      const sourceId = nodeMap.get(rel.start)
      const targetId = nodeMap.get(rel.end)
      
      if (sourceId && targetId) {
        code += `    ${sourceId} -->|${rel.type}| ${targetId}\n`
      }
    })
    
    code += '\n'
    
    // 스타일 정의 - 모든 노드 동일한 색상
    data.nodes.forEach((_node, index) => {
      const nodeId = `N${index}`
      const color = '#0052a3' // 오방색 파란색으로 통일
      
      code += `    style ${nodeId} fill:${color},stroke:#e5e7eb,stroke-width:2px,color:#fff\n`
    })
    
    return code
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()

    if (!question.trim()) {
      setAnswer('질문을 입력해 주세요.')
      return
    }

    setIsLoading(true)
    setAnswer('질문을 분석하고, 그래프를 조회하는 중입니다...')
    setGraphData(null)

    try {
      const response = await fetch('/api/ask', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: question,
          mode: mode,
        }),
      })

      if (!response.ok) {
        const errorBody = await response.json().catch(() => ({}))
        throw new Error(errorBody.error || `요청 실패 (status: ${response.status})`)
      }

      const data = await response.json()
      setAnswer(data.answer || '응답은 받았지만, 내용이 비어 있습니다.')
      setGraphData(data.graphData || null)
    } catch (err: any) {
      console.error(err)
      setAnswer(
        `요청 중 오류가 발생했습니다.\n\n에러 메시지: ${
          err.message || '알 수 없는 오류'
        }`
      )
      setGraphData(null)
    } finally {
      setIsLoading(false)
    }
  }

  const handleClear = () => {
    setQuestion('')
    setAnswer(null)
    setGraphData(null)
  }

  const handleZoomIn = () => {
    setZoom((prev) => Math.min(prev + 0.2, 3))
  }

  const handleZoomOut = () => {
    setZoom((prev) => Math.max(prev - 0.2, 0.5))
  }

  const handleZoomReset = () => {
    setZoom(1)
  }

  return (
    <div className="app-root">
      <header className="app-header">
        <div className="app-title-block">
          <span className="app-title-korean">조선 왕조 실록 해체 분석기</span>
          <span className="app-title-english">Joseon GraphRAG System</span>
        </div>
        
        <div className="mode-selector">
          <label htmlFor="mode-select">검색 모드:</label>
          <select
            id="mode-select"
            value={mode}
            onChange={(e) => setMode(e.target.value as any)}
            className="mode-select"
          >
            <option value="hybrid">하이브리드 (권장)</option>
            <option value="vector">벡터 검색</option>
            <option value="keyword">키워드 검색</option>
            <option value="cypher">Cypher 검색</option>
            <option value="global">글로벌 검색 (Louvain)</option>
          </select>
        </div>
      </header>

      <main className="app-layout">
        {/* 왼쪽: 질문 + 답변 */}
        <section className="panel panel-left">
          {/* 1번칸 - 질문 입력 */}
          <div className="panel-section panel-input">
            <div className="panel-header panel-header-input">
              <span className="panel-label">1</span>
              <span className="panel-title">질문 입력</span>
            </div>
            <form className="input-form" onSubmit={handleSubmit}>
              <textarea
                className="question-textarea"
                placeholder="무엇이든 물어보세요... (예: 세종의 아버지는?, 태종이 편찬한 책은?)"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                disabled={isLoading}
              />
              <div className="input-actions">
                <button
                  type="button"
                  className="secondary-button"
                  onClick={handleClear}
                  disabled={isLoading}
                >
                  초기화
                </button>
                <button
                  type="submit"
                  className="primary-button"
                  disabled={!question.trim() || isLoading}
                >
                  {isLoading && <span className="loading-spinner"></span>}
                  {isLoading ? '처리 중...' : '질문 보내기'}
                </button>
              </div>
            </form>
          </div>

          {/* 2번칸 - 답변 출력 */}
          <div className="panel-section panel-answer">
            <div className="panel-header panel-header-answer">
              <span className="panel-label">2</span>
              <span className="panel-title">답변 출력</span>
            </div>
            <div className="panel-body answer-body">
              {answer ? (
                <p className="answer-text">{answer}</p>
              ) : (
                <p className="placeholder-text">
                  질문을 보내면 이 영역에 답변이 표시됩니다.
                </p>
              )}
            </div>
          </div>
        </section>

        {/* 오른쪽: 그래프 시각화 */}
        <section className="panel panel-right">
          <div className="panel-section panel-graph">
            <div className="panel-header panel-header-graph">
              <span className="panel-label">3</span>
              <span className="panel-title">Neo4j 그래프 시각화 (Mermaid)</span>
              {graphData && graphData.nodes.length > 0 && (
                <div className="zoom-controls">
                  <button
                    className="zoom-button"
                    onClick={handleZoomOut}
                    title="축소 (Ctrl + 마우스휠)"
                  >
                    −
                  </button>
                  <span className="zoom-level">{Math.round(zoom * 100)}%</span>
                  <button
                    className="zoom-button"
                    onClick={handleZoomIn}
                    title="확대 (Ctrl + 마우스휠)"
                  >
                    +
                  </button>
                  <button
                    className="zoom-button zoom-reset"
                    onClick={handleZoomReset}
                    title="리셋"
                  >
                    ⟲
                  </button>
                </div>
              )}
            </div>
            <div className="panel-body graph-body" ref={graphContainerRef}>
              {graphData && graphData.nodes.length > 0 ? (
                <div className="mermaid-wrapper">
                  <div
                    className="mermaid-container"
                    ref={mermaidRef}
                    style={{
                      transform: `scale(${zoom})`,
                      transformOrigin: 'center center',
                    }}
                  ></div>
                </div>
              ) : (
                <div className="graph-placeholder">
                  <p className="graph-placeholder-title">그래프 미리보기 영역</p>
                  <p className="graph-placeholder-desc">
                    Neo4j에서 추출한 그래프를 이 영역에 Mermaid.js로 렌더링합니다.
                    <br />
                    질문을 보내면 관련 노드와 관계가 시각화됩니다.
                  </p>
                </div>
              )}
            </div>
          </div>
        </section>
      </main>
    </div>
  )
}

export default App
