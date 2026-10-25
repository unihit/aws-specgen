# AWS CloudShell 인프라 생성 명세서 자동 생성기 (AWS SpecGen)

> **보안 컴플라이언스 준수 & 고객사 제출용 공식 산출물 표준**  
> 고객사 환경에 영구 Access Key를 발급하거나 외부 터널을 뚫을 필요 없이,  
> **[1단계] 고객사 CloudShell에서 임시 세션 권한으로 안전하게 JSON 추출** ➔ **[2단계] 로컬 브라우저에서 JSON Drag & Drop ➔ 고객사용 고품격 엑셀(.xlsx) 생성**

---

## 🏗️ 2단계 워크플로우 아키텍처

```
[고객사 AWS 환경]                              [엔지니어 로컬 PC 환경]
+-------------------------------+             +---------------------------------------+
|  AWS CloudShell 터미널        |             |  웹 브라우저 (viewer/index.html)     |
|                               |             |                                       |
|  $ python3 scan_cloudshell.py |             |  1. JSON 파일 Drag & Drop             |
|          ↓                    |             |  2. 인프라 대시보드 미리보기 검토      |
|  aws_spec_ap-northeast-2.json |  [다운로드]  |  3. [고객사 제출용 엑셀 다운로드] 클릭  |
|          ↓                    | ===========>|          ↓                            |
|  Actions -> Download file     |             |  AWS_인프라_생성명세서_(주)고객사.xlsx |
+-------------------------------+             +---------------------------------------+
(※ 외부 pip 설치 불필요 / 세션 자격증명)       (※ 100% 브라우저 메모리 처리 / 데이터 유출 없음)
```

---

## 🚀 빠른 시작 가이드 (2단계)

### [Step 1] 고객사 AWS CloudShell에서 실행

1. 고객사 AWS 콘솔 상단의 **CloudShell** 아이콘을 클릭하여 터미널을 엽니다.
2. 터미널에 아래 **원라이너 명령어**를 복사-붙여넣기하여 즉시 실행합니다 (외부 라이브러리 설치 불필요):

```bash
# CloudShell에서 1줄로 스크립트 다운로드 및 즉시 스캔
curl -sLO https://raw.githubusercontent.com/unihit/aws-specgen/main/scan_cloudshell.py && python3 scan_cloudshell.py
```

3. 실행 완료 후 화면에 표시된 파일명을 확인합니다 (예: `aws_spec_ap-northeast-2.json`).
4. **CloudShell 화면 우측 상단의 [Actions] ➔ [Download file]** 클릭 ➔ 파일명을 입력하고 로컬 PC로 다운로드합니다.

> 💡 **보안 안내**: `scan_cloudshell.py`는 `ReadOnly` 권한만 사용하며, 패스워드/UserData/Lambda 환경변수 등의 민감정보는 일체 수집하지 않습니다.

---

### [Step 2] 로컬 브라우저에서 엑셀 생성

1. 로컬 PC의 [`viewer/index.html`](file:///C:/Users/wnsla/.gemini/antigravity/scratch/aws-specgen/viewer/index.html) 파일을 **더블 클릭**하여 브라우저(Chrome/Edge 등)에서 엽니다.
   *(또는 로컬에서 `python -m http.server 8080` 후 `http://localhost:8080/viewer` 접속)*
2. 화면 중앙의 업로드 영역에 Step 1에서 받은 **`aws_spec_*.json` 파일을 Drag & Drop** 합니다.
3. 브라우저 화면에 리소스 KPI 및 테이블이 시각화되면, 상단 입력창에 **고객사 명칭**을 입력합니다.
4. 초록색 **[고객사 제출용 엑셀 명세서 다운로드 (.xlsx)]** 버튼을 클릭하면 최종 납품용 엑셀이 즉시 다운로드됩니다!

---

## 📊 엑셀 명세서 시트 구성 (ExcelJS 슬레이트 네이비 테마)

| 번호 | 시트 명칭 | 주요 포함 정보 |
| :--- | :--- | :--- |
| **00** | **인프라_요약_보고서** | 고객사명, 계정 ID, 리전, 스캔 일시, 자원별 총 수량 KPI 카드 |
| **01** | **네트워크_VPC** | VPC 이름, VPC ID, CIDR 블록, 기본 VPC 여부, 상태, DHCP ID |
| **02** | **서브넷_Subnet** | 서브넷명, Subnet ID, 소속 VPC, CIDR, 가용영역(AZ), 망 구분(Public/Private), 가용 IP |
| **03** | **게이트웨이** | 인터넷 게이트웨이(IGW), NAT 게이트웨이(EIP 매핑), 연결 VPC |
| **04** | **라우팅테이블** | Route Table ID, 연결 서브넷, 기본 게이트웨이(0.0.0.0/0 타겟), 주요 라우팅 요약 |
| **05** | **보안그룹** | Security Group ID, 그룹명, 소속 VPC, 인바운드 허용 룰(포트/소스 대역) 요약 |
| **06** | **컴퓨팅_EC2** | 인스턴스 Name, Instance ID, 상태, 인스턴스 타입, Private/Public IP, AZ, EBS 용량 |
| **07** | **데이터베이스_RDS** | DB 식별자, 상태, 엔진 및 버전, 인스턴스 클래스, 스토리지 용량, Multi-AZ, 엔드포인트 |
| **08** | **로드밸런서_ELB** | ALB/NLB 명칭, 유형, 스킴(인터넷/내부), DNS 엔드포인트, 리스너 포트 |
| **09** | **스토리지_S3** | 버킷 이름, 배치 리전, 기본 암호화, 버전 관리 상태, 퍼블릭 차단 여부 |
| **10** | **서버리스_Lambda** | 함수명, 런타임, 할당 메모리, 타임아웃, 핸들러, 실행 역할(IAM) |

---

## 📁 디렉터리 구조

```
aws-specgen/
├── scan_cloudshell.py              # [Step 1] 고객사 CloudShell 실행용 단일 스크립트 (Zero pip install)
├── viewer/                         # [Step 2] 로컬 브라우저 뷰어 & 엑셀 생성기
│   ├── index.html                  # 정적 웹 대시보드 UI
│   ├── app.js                      # 100% 클라이언트 사이드 JSON 파싱 & ExcelJS 변환기
│   └── vendor/
│       └── exceljs.min.js          # 로컬 오프라인 번들
├── sample_aws_spec_ap-northeast-2.json # 즉시 테스트 가능한 샘플 스캔 데이터
└── README.md                       # 사용 설명서
```
