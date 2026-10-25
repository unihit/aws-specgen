#!/usr/bin/env bash
# ==============================================================================
# AWS Infrastructure Specification Generator - CloudShell Launcher
# ==============================================================================

set -e

echo "======================================================================"
echo " [AWS 인프라 생성 명세서 자동 생성기 - CloudShell]"
echo "======================================================================"

# 1. 필수 라이브러리 자동 설치
echo "[1/3] 필수 의존 패키지(flask, openpyxl, boto3) 확인 및 설치..."
pip3 install -q -r requirements.txt

# 2. 리전 환경변수 확인
TARGET_REGION=${AWS_REGION:-${AWS_DEFAULT_REGION:-"ap-northeast-2"}}
echo "[2/3] 기준 리전 감지: ${TARGET_REGION}"

# 3. 실행 모드 선택
echo "[3/3] 실행 모드를 선택하세요:"
echo " 1) [추천] CLI 즉시 추출 모드 (1초 만에 엑셀 생성 -> CloudShell Actions에서 다운로드)"
echo " 2) 웹 브라우저 UI 모드 (Flask 대시보드 8080 포트 실행)"
read -p "선택 (1 또는 2, 기본값 1): " MODE

if [ "$MODE" = "2" ]; then
    echo "----------------------------------------------------------------------"
    echo " 웹 브라우저 서버(포트 8080)를 실행합니다..."
    echo " CloudShell 접속 터널링 또는 브라우저 주소: http://127.0.0.1:8080"
    echo " (종료하려면 Ctrl + C)"
    echo "----------------------------------------------------------------------"
    python3 app.py --port 8080
else
    read -p "고객사 명칭을 입력하세요 (기본값: 고객사): " CUSTOMER_NAME
    CUSTOMER_NAME=${CUSTOMER_NAME:-"고객사"}
    echo "----------------------------------------------------------------------"
    python3 app.py --cli --customer "$CUSTOMER_NAME" --region "$TARGET_REGION"
fi
