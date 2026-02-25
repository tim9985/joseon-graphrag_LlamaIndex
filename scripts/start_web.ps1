# 조선왕조 GraphRAG 웹 서버 실행 스크립트

Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "조선왕조 GraphRAG 웹 애플리케이션 시작" -ForegroundColor Yellow
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

# 1. 사전 체크
Write-Host "[1/4] 사전 요구사항 확인 중..." -ForegroundColor Green

# Python 확인
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  ✓ Python: $pythonVersion" -ForegroundColor Gray
} catch {
    Write-Host "  ✗ Python이 설치되지 않았습니다!" -ForegroundColor Red
    exit 1
}

# Node.js 확인
try {
    $nodeVersion = node --version 2>&1
    Write-Host "  ✓ Node.js: $nodeVersion" -ForegroundColor Gray
} catch {
    Write-Host "  ✗ Node.js가 설치되지 않았습니다!" -ForegroundColor Red
    exit 1
}

Write-Host ""

# 2. 의존성 확인
Write-Host "[2/4] 의존성 확인 중..." -ForegroundColor Green

if (!(Test-Path "node_modules")) {
    Write-Host "  → Node.js 의존성 설치 중..." -ForegroundColor Yellow
    npm install
}

Write-Host "  ✓ 의존성 준비 완료" -ForegroundColor Gray
Write-Host ""

# 3. 환경 변수 확인
Write-Host "[3/4] 환경 설정 확인 중..." -ForegroundColor Green

if (!(Test-Path ".env")) {
    Write-Host "  ⚠ .env 파일이 없습니다. 기본값을 사용합니다." -ForegroundColor Yellow
} else {
    Write-Host "  ✓ .env 파일 확인됨" -ForegroundColor Gray
}

Write-Host ""

# 4. 서버 실행
Write-Host "[4/4] 서버 시작 중..." -ForegroundColor Green
Write-Host ""

Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "백엔드 (Flask) 및 프론트엔드 (React)를 시작합니다." -ForegroundColor Yellow
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""
Write-Host "  • 백엔드 API: http://localhost:5001" -ForegroundColor Cyan
Write-Host "  • 프론트엔드: http://localhost:3000 (자동으로 브라우저가 열립니다)" -ForegroundColor Cyan
Write-Host ""
Write-Host "종료하려면:" -ForegroundColor Yellow
Write-Host "  1. 이 창에서 Ctrl+C 누르기" -ForegroundColor Gray
Write-Host "  2. React 개발 서버 터미널에서 Ctrl+C 누르기" -ForegroundColor Gray
Write-Host ""
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

# Flask 백엔드를 백그라운드 Job으로 시작
$backendJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    python backend/qa_api.py
}

Write-Host "  ✓ 백엔드 서버 시작됨 (Job ID: $($backendJob.Id))" -ForegroundColor Green

# 백엔드가 준비될 때까지 대기
Start-Sleep -Seconds 3

Write-Host "  → 프론트엔드 서버 시작 중..." -ForegroundColor Yellow
Write-Host ""

# React 프론트엔드 실행 (메인 프로세스)
try {
    npm start
} finally {
    # 정리: 백엔드 Job 종료
    Write-Host ""
    Write-Host "정리 중..." -ForegroundColor Yellow
    Stop-Job -Job $backendJob
    Remove-Job -Job $backendJob
    Write-Host "백엔드 서버 종료됨" -ForegroundColor Gray
}
