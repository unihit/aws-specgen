"""
AWS Infrastructure Specification Web & CLI Generator.
CloudShell 기본 리전 자동 감지 및 고객사 제출용 엑셀 명세서 추출.
"""

import os
import sys
import argparse
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
from collector import AWSResourceCollector, get_default_region
from excel_generator import ExcelReportBuilder

app = Flask(__name__)

# 인메모리 스캔 캐시 (세션 유지)
LATEST_SCAN_CACHE = {}


@app.route("/")
def index():
    default_region = get_default_region()
    return render_template("index.html", default_region=default_region)


@app.route("/api/scan", methods=["POST"])
def scan():
    try:
        body = request.get_json() or {}
        customer = body.get("customer", "고객사")
        region = body.get("region") or get_default_region()

        collector = AWSResourceCollector(region=region)
        data = collector.collect_all()

        # 캐시 저장
        cache_key = f"{customer}_{region}"
        LATEST_SCAN_CACHE[cache_key] = data
        LATEST_SCAN_CACHE["last"] = {"data": data, "customer": customer, "region": region}

        return jsonify({
            "status": "success",
            "message": "인프라 스캔이 완료되었습니다.",
            "data": data
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route("/api/download", methods=["GET"])
def download():
    try:
        customer = request.args.get("customer", "고객사")
        region = request.args.get("region") or get_default_region()

        cache_key = f"{customer}_{region}"
        data = LATEST_SCAN_CACHE.get(cache_key)

        if not data:
            # 캐시가 없으면 즉시 스캔 수행
            collector = AWSResourceCollector(region=region)
            data = collector.collect_all()

        builder = ExcelReportBuilder(data, customer_name=customer)
        excel_stream = builder.save_to_bytes()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"AWS_인프라_생성명세서_{region}_{timestamp}.xlsx"

        # RFC 5987 표준 인코딩 처리
        import urllib.parse
        encoded_filename = urllib.parse.quote(filename)

        response = send_file(
            excel_stream,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename
        )
        response.headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{encoded_filename}"
        return response
    except Exception as e:
        return f"엑셀 다운로드 오류: {str(e)}", 500


def run_cli_mode(customer: str, region: str = None, output_file: str = None):
    """CloudShell CLI 원클릭 엑셀 생성 모드"""
    target_region = region or get_default_region()
    print("=" * 65)
    print(" [AWS 인프라 생성 명세서 자동 생성기 - CloudShell CLI Mode]")
    print(f" - 대상 고객사: {customer}")
    print(f" - 기준 리전  : {target_region}")
    print("=" * 65)

    print("\n[1/2] AWS 핵심 코어 및 네트워크 자원을 수집하는 중...")
    collector = AWSResourceCollector(region=target_region)
    data = collector.collect_all()
    summary = data.get("summary", {})

    print(f"  √ VPC {summary.get('vpc_count', 0)}개, 서브넷 {summary.get('subnet_count', 0)}개, 보안그룹 {summary.get('sg_count', 0)}개")
    print(f"  √ EC2 {summary.get('ec2_count', 0)}대, RDS {summary.get('rds_count', 0)}개, ELB {summary.get('elb_count', 0)}대")
    print(f"  √ S3 {summary.get('s3_count', 0)}개, Lambda {summary.get('lambda_count', 0)}개 수집 완료")

    print("\n[2/2] 고객사 제출용 엑셀 보고서 서식 작성 및 스타일링 중...")
    builder = ExcelReportBuilder(data, customer_name=customer)

    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        output_file = f"AWS_인프라_생성명세서_{target_region}_{timestamp}.xlsx"

    builder.save_to_file(output_file)

    print("=" * 65)
    print(" [성공] 엑셀 명세서가 성공적으로 생성되었습니다!")
    print(f"  -> 생성 파일: {os.path.abspath(output_file)}")
    print("=" * 65)
    print("\n [CloudShell 다운로드 방법]")
    print(" 1. AWS CloudShell 화면 우측 상단의 [Actions] 메뉴 클릭")
    print(" 2. [Download file] 선택")
    print(f" 3. 파일 경로에 아래 파일명을 입력 후 다운로드:")
    print(f"    {output_file}")
    print("=" * 65)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AWS 인프라 생성 명세서 웹 & CLI 생성기")
    parser.add_argument("--cli", action="store_true", help="웹 서버를 띄우지 않고 CLI 모드로 즉시 엑셀 생성")
    parser.add_argument("--customer", default="고객사", help="고객사 명칭")
    parser.add_argument("--region", default=None, help="대상 AWS 리전 (생략 시 CloudShell 리전 자동 감지)")
    parser.add_argument("--output", default=None, help="출력 엑셀 파일명")
    parser.add_argument("--port", type=int, default=8080, help="웹 서버 포트 (기본: 8080)")
    parser.add_argument("--host", default="0.0.0.0", help="웹 서버 호스트 바인딩")

    args = parser.parse_args()

    if args.cli:
        run_cli_mode(customer=args.customer, region=args.region, output_file=args.output)
    else:
        detected_region = get_default_region()
        print("=" * 65)
        print(" [AWS 인프라 생성 명세서 생성기 웹 서버 시작]")
        print(f" - 감지된 CloudShell 기본 리전: {detected_region}")
        print(f" - 웹 브라우저 접속 주소: http://127.0.0.1:{args.port} 또는 http://localhost:{args.port}")
        print("=" * 65)
        app.run(host=args.host, port=args.port, debug=False)
