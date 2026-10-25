"""
AWS Resource Collector for Infrastructure Specification.
CloudShell 환경의 기본 리전을 자동 감지하고, 고객사 보고용 핵심 코어 및 네트워크 자원을 깔끔하게 추출합니다.
"""

import os
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from datetime import datetime

# 인스턴스 타입별 vCPU / RAM(GiB) 카탈로그 (대표적인 일반 타입 캐시, API 실패 시 폴백용)
COMMON_INSTANCE_SPECS = {
    "t2.nano": (1, 0.5), "t2.micro": (1, 1), "t2.small": (1, 2), "t2.medium": (2, 4), "t2.large": (2, 8),
    "t3.nano": (2, 0.5), "t3.micro": (2, 1), "t3.small": (2, 2), "t3.medium": (2, 4), "t3.large": (2, 8), "t3.xlarge": (4, 16), "t3.2xlarge": (8, 32),
    "t4g.nano": (2, 0.5), "t4g.micro": (2, 1), "t4g.small": (2, 2), "t4g.medium": (2, 4), "t4g.large": (2, 8), "t4g.xlarge": (4, 16),
    "m5.large": (2, 8), "m5.xlarge": (4, 16), "m5.2xlarge": (8, 32), "m5.4xlarge": (16, 64),
    "m6i.large": (2, 8), "m6i.xlarge": (4, 16), "m6i.2xlarge": (8, 32),
    "m6g.large": (2, 8), "m6g.xlarge": (4, 16), "m6g.2xlarge": (8, 32),
    "c5.large": (2, 4), "c5.xlarge": (4, 8), "c5.2xlarge": (8, 16), "c5.4xlarge": (16, 32),
    "c6i.large": (2, 4), "c6i.xlarge": (4, 8), "c6i.2xlarge": (8, 16),
    "r5.large": (2, 16), "r5.xlarge": (4, 32), "r5.2xlarge": (8, 64),
    "r6i.large": (2, 16), "r6i.xlarge": (4, 32), "r6i.2xlarge": (8, 64),
}


def get_default_region() -> str:
    """CloudShell 환경변수 및 boto3 기본 리전 자동 감지"""
    # 1. CloudShell 환경변수 우선 확인
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
    if region:
        return region

    # 2. boto3 session 기본 설정 확인
    try:
        session = boto3.session.Session()
        if session.region_name:
            return session.region_name
    except Exception:
        pass

    # 3. 한국 사용자 기본값: ap-northeast-2 (서울)
    return "ap-northeast-2"


def get_tag_value(tags, key="Name", default="-"):
    """AWS Tags 리스트에서 특정 키값 추출"""
    if not tags:
        return default
    for tag in tags:
        if tag.get("Key") == key:
            return tag.get("Value", default)
    return default


class AWSResourceCollector:
    def __init__(self, region: str = None):
        self.region = region or get_default_region()
        self.session = boto3.session.Session(region_name=self.region)

    def collect_all(self) -> dict:
        """모든 핵심 코어 및 네트워크 자원을 수집"""
        results = {
            "metadata": {
                "region": self.region,
                "scanned_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
            "vpcs": self.collect_vpcs(),
            "subnets": self.collect_subnets(),
            "gateways": self.collect_gateways(),
            "route_tables": self.collect_route_tables(),
            "security_groups": self.collect_security_groups(),
            "ec2_instances": self.collect_ec2(),
            "rds_instances": self.collect_rds(),
            "load_balancers": self.collect_load_balancers(),
            "s3_buckets": self.collect_s3(),
            "lambda_functions": self.collect_lambda(),
        }

        # 요약 통계 집계
        results["summary"] = {
            "vpc_count": len(results["vpcs"]),
            "subnet_count": len(results["subnets"]),
            "igw_count": len(results["gateways"].get("igw", [])),
            "nat_count": len(results["gateways"].get("nat", [])),
            "sg_count": len(results["security_groups"]),
            "ec2_count": len(results["ec2_instances"]),
            "rds_count": len(results["rds_instances"]),
            "elb_count": len(results["load_balancers"]),
            "s3_count": len(results["s3_buckets"]),
            "lambda_count": len(results["lambda_functions"]),
        }
        return results

    def collect_vpcs(self) -> list:
        """VPC 목록 수집"""
        vpcs = []
        try:
            ec2 = self.session.client("ec2")
            res = ec2.describe_vpcs()
            for v in res.get("Vpcs", []):
                vpc_id = v.get("VpcId", "")
                name = get_tag_value(v.get("Tags"), "Name", default="(No Name)")
                cidr = v.get("CidrBlock", "")
                is_default = "예 (기본)" if v.get("IsDefault") else "아니오 (사용자 생성)"
                state = v.get("State", "")
                dhcp = v.get("DhcpOptionsId", "-")
                vpcs.append({
                    "name": name,
                    "vpc_id": vpc_id,
                    "cidr": cidr,
                    "is_default": is_default,
                    "state": state,
                    "dhcp": dhcp
                })
        except Exception as e:
            print(f"[Warning] VPC 수집 오류: {e}")
        return vpcs

    def collect_subnets(self) -> list:
        """서브넷 목록 수집 (퍼블릭/프라이빗 추정 포함)"""
        subnets = []
        try:
            ec2 = self.session.client("ec2")
            # 라우팅 테이블 정보를 미리 가져와서 퍼블릭 서브넷 판별에 활용
            rtb_res = ec2.describe_route_tables()
            public_subnet_ids = set()
            for rtb in rtb_res.get("RouteTables", []):
                has_igw = any(r.get("GatewayId", "").startswith("igw-") for r in rtb.get("Routes", []))
                if has_igw:
                    for assoc in rtb.get("Associations", []):
                        sub_id = assoc.get("SubnetId")
                        if sub_id:
                            public_subnet_ids.add(sub_id)

            res = ec2.describe_subnets()
            for s in res.get("Subnets", []):
                sub_id = s.get("SubnetId", "")
                name = get_tag_value(s.get("Tags"), "Name", default="(No Name)")
                vpc_id = s.get("VpcId", "")
                cidr = s.get("CidrBlock", "")
                az = s.get("AvailabilityZone", "")
                avail_ip = s.get("AvailableIpAddressCount", 0)
                sub_type = "Public" if (sub_id in public_subnet_ids or s.get("MapPublicIpOnLaunch")) else "Private"
                state = s.get("State", "")

                subnets.append({
                    "name": name,
                    "subnet_id": sub_id,
                    "vpc_id": vpc_id,
                    "cidr": cidr,
                    "az": az,
                    "type": sub_type,
                    "available_ips": avail_ip,
                    "state": state
                })
            subnets.sort(key=lambda x: (x["vpc_id"], x["az"], x["name"]))
        except Exception as e:
            print(f"[Warning] Subnet 수집 오류: {e}")
        return subnets

    def collect_gateways(self) -> dict:
        """IGW 및 NAT Gateway 수집"""
        gateways = {"igw": [], "nat": []}
        try:
            ec2 = self.session.client("ec2")
            # IGW
            igw_res = ec2.describe_internet_gateways()
            for igw in igw_res.get("InternetGateways", []):
                igw_id = igw.get("InternetGatewayId", "")
                name = get_tag_value(igw.get("Tags"), "Name", default="-")
                attached_vpcs = ", ".join([a.get("VpcId", "") for a in igw.get("Attachments", [])])
                gateways["igw"].append({
                    "name": name,
                    "igw_id": igw_id,
                    "attached_vpc": attached_vpcs or "연결 없음",
                    "state": igw.get("Attachments", [{}])[0].get("State", "-") if igw.get("Attachments") else "-"
                })

            # NAT Gateway
            nat_res = ec2.describe_nat_gateways()
            for nat in nat_res.get("NatGateways", []):
                if nat.get("State") == "deleted":
                    continue
                nat_id = nat.get("NatGatewayId", "")
                name = get_tag_value(nat.get("Tags"), "Name", default="-")
                vpc_id = nat.get("VpcId", "")
                subnet_id = nat.get("SubnetId", "")
                state = nat.get("State", "")
                eips = [addr.get("PublicIp", "") for addr in nat.get("NatGatewayAddresses", []) if addr.get("PublicIp")]
                gateways["nat"].append({
                    "name": name,
                    "nat_id": nat_id,
                    "vpc_id": vpc_id,
                    "subnet_id": subnet_id,
                    "state": state,
                    "public_ip": ", ".join(eips) or "-"
                })
        except Exception as e:
            print(f"[Warning] Gateways 수집 오류: {e}")
        return gateways

    def collect_route_tables(self) -> list:
        """라우팅 테이블 수집 (간결한 핵심 정보)"""
        tables = []
        try:
            ec2 = self.session.client("ec2")
            res = ec2.describe_route_tables()
            for rtb in res.get("RouteTables", []):
                rtb_id = rtb.get("RouteTableId", "")
                name = get_tag_value(rtb.get("Tags"), "Name", default="-")
                vpc_id = rtb.get("VpcId", "")

                # 연결된 서브넷 목록
                subnets = [a.get("SubnetId") for a in rtb.get("Associations", []) if a.get("SubnetId")]
                is_main = any(a.get("Main", False) for a in rtb.get("Associations", []))
                subnets_str = ", ".join(subnets) if subnets else ("(Main RTB)" if is_main else "-")

                # 주요 라우트 요약 (예: 0.0.0.0/0 목적지 타겟)
                default_target = "-"
                all_routes = []
                for r in rtb.get("Routes", []):
                    dest = r.get("DestinationCidrBlock") or r.get("DestinationIpv6CidrBlock") or r.get("DestinationPrefixListId", "")
                    target = (
                        r.get("GatewayId") or r.get("NatGatewayId") or r.get("TransitGatewayId") or
                        r.get("VpcPeeringConnectionId") or r.get("NetworkInterfaceId") or "local"
                    )
                    all_routes.append(f"{dest} -> {target}")
                    if dest == "0.0.0.0/0":
                        default_target = target

                tables.append({
                    "name": name,
                    "rtb_id": rtb_id,
                    "vpc_id": vpc_id,
                    "associated_subnets": subnets_str,
                    "default_gateway": default_target,
                    "routes_summary": " | ".join(all_routes[:4]) + ("..." if len(all_routes) > 4 else "")
                })
        except Exception as e:
            print(f"[Warning] Route Tables 수집 오류: {e}")
        return tables

    def collect_security_groups(self) -> list:
        """보안 그룹 수집 및 허용 포트 깔끔 정리"""
        sgs = []
        try:
            ec2 = self.session.client("ec2")
            res = ec2.describe_security_groups()
            for sg in res.get("SecurityGroups", []):
                sg_id = sg.get("GroupId", "")
                group_name = sg.get("GroupName", "")
                name = get_tag_value(sg.get("Tags"), "Name", default=group_name)
                vpc_id = sg.get("VpcId", "-")
                description = sg.get("Description", "-")

                # 인바운드 룰 요약
                inbound_summary = []
                for perm in sg.get("IpPermissions", []):
                    proto = perm.get("IpProtocol", "all")
                    from_port = perm.get("FromPort")
                    to_port = perm.get("ToPort")
                    if proto == "-1":
                        port_str = "All Traffic"
                    elif from_port == to_port:
                        port_str = f"{proto}:{from_port}" if from_port is not None else proto
                    else:
                        port_str = f"{proto}:{from_port}-{to_port}"

                    sources = []
                    for ip_range in perm.get("IpRanges", []):
                        sources.append(ip_range.get("CidrIp", ""))
                    for user_sg in perm.get("UserIdGroupPairs", []):
                        sources.append(user_sg.get("GroupId", ""))

                    src_str = ",".join(sources[:2]) + (".." if len(sources) > 2 else "")
                    inbound_summary.append(f"[{port_str} from {src_str}]")

                sgs.append({
                    "name": name,
                    "group_id": sg_id,
                    "group_name": group_name,
                    "vpc_id": vpc_id,
                    "description": description,
                    "inbound_rules": " \n".join(inbound_summary) if inbound_summary else "규칙 없음",
                    "inbound_rule_count": len(sg.get("IpPermissions", []))
                })
        except Exception as e:
            print(f"[Warning] Security Group 수집 오류: {e}")
        return sgs

    def collect_ec2(self) -> list:
        """EC2 인스턴스 수집"""
        instances = []
        try:
            ec2 = self.session.client("ec2")
            res = ec2.describe_instances()
            for resv in res.get("Reservations", []):
                for inst in resv.get("Instances", []):
                    # 종료(terminated) 상태는 제외하거나 표기
                    state = inst.get("State", {}).get("Name", "")
                    if state == "terminated":
                        continue

                    inst_id = inst.get("InstanceId", "")
                    name = get_tag_value(inst.get("Tags"), "Name", default="(No Name)")
                    inst_type = inst.get("InstanceType", "")
                    az = inst.get("Placement", {}).get("AvailabilityZone", "")
                    private_ip = inst.get("PrivateIpAddress", "-")
                    public_ip = inst.get("PublicIpAddress", "-")
                    subnet_id = inst.get("SubnetId", "-")
                    vpc_id = inst.get("VpcId", "-")
                    key_name = inst.get("KeyName", "-")

                    # 사양 조회 (vCPU, RAM)
                    vcpu, ram = COMMON_INSTANCE_SPECS.get(inst_type, ("-", "-"))

                    launch_time = inst.get("LaunchTime")
                    launch_str = launch_time.strftime("%Y-%m-%d %H:%M") if launch_time else "-"

                    instances.append({
                        "name": name,
                        "instance_id": inst_id,
                        "state": state,
                        "instance_type": inst_type,
                        "vcpu": vcpu,
                        "ram_gib": ram,
                        "private_ip": private_ip,
                        "public_ip": public_ip,
                        "vpc_id": vpc_id,
                        "subnet_id": subnet_id,
                        "az": az,
                        "key_name": key_name,
                        "launch_time": launch_str
                    })
            instances.sort(key=lambda x: (x["state"] != "running", x["name"]))
        except Exception as e:
            print(f"[Warning] EC2 수집 오류: {e}")
        return instances

    def collect_rds(self) -> list:
        """RDS 인스턴스 및 오로라 클러스터 수집"""
        databases = []
        try:
            rds = self.session.client("rds")
            res = rds.describe_db_instances()
            for db in res.get("DBInstances", []):
                db_id = db.get("DBInstanceIdentifier", "")
                engine = f"{db.get('Engine', '')} {db.get('EngineVersion', '')}"
                db_class = db.get("DBInstanceClass", "")
                storage = f"{db.get('AllocatedStorage', 0)} GB ({db.get('StorageType', '')})"
                multi_az = "예 (Multi-AZ)" if db.get("MultiAZ") else "아니오 (Single-AZ)"
                status = db.get("DBInstanceStatus", "")

                endpoint = db.get("Endpoint", {}).get("Address", "-")
                port = db.get("Endpoint", {}).get("Port", "-")
                endpoint_str = f"{endpoint}:{port}" if endpoint != "-" else "-"

                subnet_grp = db.get("DBSubnetGroup", {})
                vpc_id = subnet_grp.get("VpcId", "-")
                subnet_grp_name = subnet_grp.get("DBSubnetGroupName", "-")

                databases.append({
                    "db_id": db_id,
                    "engine": engine,
                    "db_class": db_class,
                    "storage": storage,
                    "multi_az": multi_az,
                    "status": status,
                    "endpoint": endpoint_str,
                    "vpc_id": vpc_id,
                    "subnet_group": subnet_grp_name
                })
        except Exception as e:
            print(f"[Warning] RDS 수집 오류: {e}")
        return databases

    def collect_load_balancers(self) -> list:
        """ALB / NLB (ELBv2) 수집"""
        elbs = []
        try:
            elbv2 = self.session.client("elbv2")
            res = elbv2.describe_load_balancers()
            for lb in res.get("LoadBalancers", []):
                name = lb.get("LoadBalancerName", "")
                lb_arn = lb.get("LoadBalancerArn", "")
                lb_type = lb.get("Type", "application")
                scheme = "인터넷 연결(internet-facing)" if lb.get("Scheme") == "internet-facing" else "내부 전용(internal)"
                dns_name = lb.get("DNSName", "-")
                vpc_id = lb.get("VpcId", "-")
                state = lb.get("State", {}).get("Code", "-")

                # 리스너 포트 수집
                listener_ports = []
                try:
                    lis_res = elbv2.describe_listeners(LoadBalancerArn=lb_arn)
                    for l in lis_res.get("Listeners", []):
                        listener_ports.append(f"{l.get('Protocol', '')}:{l.get('Port', '')}")
                except Exception:
                    pass

                elbs.append({
                    "name": name,
                    "type": lb_type.upper(),
                    "scheme": scheme,
                    "dns_name": dns_name,
                    "vpc_id": vpc_id,
                    "state": state,
                    "listeners": ", ".join(listener_ports) or "-"
                })
        except Exception as e:
            print(f"[Warning] Load Balancer 수집 오류: {e}")
        return elbs

    def collect_s3(self) -> list:
        """S3 버킷 수집 (현재 리전 필터링 포함)"""
        buckets = []
        try:
            s3 = self.session.client("s3")
            res = s3.list_buckets()
            for b in res.get("Buckets", []):
                b_name = b.get("Name", "")
                created = b.get("CreationDate")
                created_str = created.strftime("%Y-%m-%d %H:%M") if created else "-"

                # 버킷 위치 확인 (글로벌 서비스이므로 현재 기준 리전 것만 선별하거나 리전 표시)
                try:
                    loc_res = s3.get_bucket_location(Bucket=b_name)
                    b_region = loc_res.get("LocationConstraint") or "us-east-1"
                except Exception:
                    b_region = "unknown"

                # 현재 작업 리전과 일치하거나 관련 있는 경우 우선 표시
                buckets.append({
                    "name": b_name,
                    "region": b_region,
                    "created_at": created_str,
                    "is_current_region": "예" if b_region == self.region else "아니오"
                })
            # 현재 리전 우선 정렬
            buckets.sort(key=lambda x: (x["is_current_region"] != "예", x["name"]))
        except Exception as e:
            print(f"[Warning] S3 수집 오류: {e}")
        return buckets

    def collect_lambda(self) -> list:
        """Lambda 함수 수집"""
        funcs = []
        try:
            lmb = self.session.client("lambda")
            paginator = lmb.get_paginator("list_functions")
            for page in paginator.paginate():
                for f in page.get("Functions", []):
                    fname = f.get("FunctionName", "")
                    runtime = f.get("Runtime", "-")
                    handler = f.get("Handler", "-")
                    memory = f"{f.get('MemorySize', 0)} MB"
                    timeout = f"{f.get('Timeout', 0)} 초"
                    last_mod = f.get("LastModified", "")[:19].replace("T", " ")

                    funcs.append({
                        "name": fname,
                        "runtime": runtime,
                        "memory": memory,
                        "timeout": timeout,
                        "handler": handler,
                        "last_modified": last_mod
                    })
        except Exception as e:
            print(f"[Warning] Lambda 수집 오류: {e}")
        return funcs
