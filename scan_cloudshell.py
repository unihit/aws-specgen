#!/usr/bin/env python3
"""
AWS CloudShell read-only infra scanner -> aws_spec_<region>.json
Only boto3 + stdlib. No secrets / env vars / userdata are collected.
"""
import os
import sys
import json
import argparse
import datetime
from concurrent.futures import ThreadPoolExecutor

try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError, BotoCoreError
except ImportError:
    sys.exit("boto3 not found. Run this inside AWS CloudShell.")

SCHEMA_VERSION = "1.0"
DENIED = {
    "AccessDenied", "AccessDeniedException", "UnauthorizedOperation",
    "UnauthorizedAccess", "AuthorizationError", "OptInRequired"
}
WARNINGS = []  # list.append is thread-safe


def tags(lst):
    return {t.get("Key"): t.get("Value") for t in (lst or [])}


def tname(lst):
    return tags(lst).get("Name", "")


def iso(v):
    return v.isoformat() if hasattr(v, "isoformat") else (v or "")


def optional(label, fn, default=None, **kw):
    """Sub-call that may fail without aborting the collector."""
    try:
        return fn(**kw)
    except ClientError as e:
        WARNINGS.append(f"{label}: {e.response['Error']['Code']}")
    except BotoCoreError as e:
        WARNINGS.append(f"{label}: {type(e).__name__}")
    return default


def pages(client, op, key, **kw):
    for p in client.get_paginator(op).paginate(**kw):
        yield from p.get(key, [])


# ---------------- collectors ----------------
def c_ec2(sess, cfg, region):
    ec2 = sess.client("ec2", config=cfg)
    vol_gb = {}
    for v in pages(ec2, "describe_volumes", "Volumes"):
        for a in v.get("Attachments", []):
            vol_gb[a["InstanceId"]] = vol_gb.get(a["InstanceId"], 0) + v.get("Size", 0)
    out = []
    for r in pages(ec2, "describe_instances", "Reservations"):
        for i in r["Instances"]:
            if i.get("State", {}).get("Name") == "terminated":
                continue
            out.append({
                "id": i["InstanceId"],
                "name": tname(i.get("Tags")),
                "type": i.get("InstanceType", ""),
                "state": i.get("State", {}).get("Name", ""),
                "az": i.get("Placement", {}).get("AvailabilityZone", ""),
                "private_ip": i.get("PrivateIpAddress", "-"),
                "public_ip": i.get("PublicIpAddress", "-"),
                "vpc_id": i.get("VpcId", "-"),
                "subnet_id": i.get("SubnetId", "-"),
                "platform": i.get("PlatformDetails", i.get("Platform", "Linux/UNIX")),
                "ami": i.get("ImageId", ""),
                "key_name": i.get("KeyName", "-"),
                "iam_profile": (i.get("IamInstanceProfile", {}).get("Arn", "").split("/")[-1]),
                "security_groups": [g["GroupId"] for g in i.get("SecurityGroups", [])],
                "ebs_total_gb": vol_gb.get(i["InstanceId"], 0),
                "launch_time": iso(i.get("LaunchTime")),
            })
    return {"ec2_instances": out}


def c_rds(sess, cfg, region):
    rds = sess.client("rds", config=cfg)
    out = []
    for d in pages(rds, "describe_db_instances", "DBInstances"):
        out.append({
            "id": d["DBInstanceIdentifier"],
            "name": d["DBInstanceIdentifier"],
            "engine": d.get("Engine", ""),
            "version": d.get("EngineVersion", ""),
            "class": d.get("DBInstanceClass", ""),
            "status": d.get("DBInstanceStatus", ""),
            "multi_az": bool(d.get("MultiAZ")),
            "az": d.get("AvailabilityZone", ""),
            "storage_gb": d.get("AllocatedStorage", 0),
            "storage_type": d.get("StorageType", ""),
            "encrypted": bool(d.get("StorageEncrypted")),
            "endpoint": (d.get("Endpoint") or {}).get("Address", "-"),
            "port": (d.get("Endpoint") or {}).get("Port", ""),
            "publicly_accessible": bool(d.get("PubliclyAccessible")),
            "vpc_id": (d.get("DBSubnetGroup") or {}).get("VpcId", "-"),
            "backup_retention_days": d.get("BackupRetentionPeriod", 0),
            "deletion_protection": bool(d.get("DeletionProtection")),
            "cluster_id": d.get("DBClusterIdentifier", ""),
        })
    return {"rds_instances": out}


def c_elbv2(sess, cfg, region):
    elb = sess.client("elbv2", config=cfg)
    out = []
    for lb in pages(elb, "describe_load_balancers", "LoadBalancers"):
        arn = lb["LoadBalancerArn"]
        ls = optional("elbv2.listeners", elb.describe_listeners, {"Listeners": []},
                      LoadBalancerArn=arn).get("Listeners", [])
        tg = optional("elbv2.targetgroups", elb.describe_target_groups,
                      {"TargetGroups": []}, LoadBalancerArn=arn).get("TargetGroups", [])
        out.append({
            "name": lb["LoadBalancerName"],
            "type": lb.get("Type", "application").upper(),
            "scheme": "internet-facing" if lb.get("Scheme") == "internet-facing" else "internal",
            "state": lb.get("State", {}).get("Code", ""),
            "dns": lb.get("DNSName", "-"),
            "vpc_id": lb.get("VpcId", "-"),
            "azs": [a.get("ZoneName", "") for a in lb.get("AvailabilityZones", [])],
            "security_groups": lb.get("SecurityGroups", []),
            "listeners": [f"{l.get('Protocol')}:{l.get('Port')}" for l in ls],
            "target_groups": [t.get("TargetGroupName", "") for t in tg],
            "created": iso(lb.get("CreatedTime")),
        })
    return {"load_balancers": out}


def c_s3(sess, cfg, region):
    s3 = sess.client("s3", config=cfg)
    out = []
    for b in s3.list_buckets().get("Buckets", []):
        n = b["Name"]
        loc = optional(f"s3.location:{n}", s3.get_bucket_location, None, Bucket=n)
        if loc is None:
            continue
        breg = loc.get("LocationConstraint") or "us-east-1"
        if breg == "EU":
            breg = "eu-west-1"
        if breg != region:
            continue
        ver = optional(f"s3.versioning:{n}", s3.get_bucket_versioning, {}, Bucket=n)
        enc = optional(f"s3.encryption:{n}", s3.get_bucket_encryption, None, Bucket=n)
        pab = optional(f"s3.pab:{n}", s3.get_public_access_block, None, Bucket=n)
        rules = ((enc or {}).get("ServerSideEncryptionConfiguration", {}).get("Rules", []))
        algo = (rules[0]["ApplyServerSideEncryptionByDefault"]["SSEAlgorithm"] if rules else "")
        cfgp = (pab or {}).get("PublicAccessBlockConfiguration", {})
        out.append({
            "name": n,
            "region": breg,
            "created": iso(b.get("CreationDate")),
            "versioning": ver.get("Status", "Disabled"),
            "encryption": algo or "None",
            "public_access_blocked": bool(cfgp) and all(cfgp.values()),
        })
    return {"s3_buckets": out}


def c_lambda(sess, cfg, region):
    lam = sess.client("lambda", config=cfg)
    out = []
    for f in pages(lam, "list_functions", "Functions"):  # Environment values intentionally dropped
        out.append({
            "name": f["FunctionName"],
            "runtime": f.get("Runtime", f.get("PackageType", "")),
            "memory_mb": f.get("MemorySize", 0),
            "timeout_s": f.get("Timeout", 0),
            "handler": f.get("Handler", "-"),
            "arch": ",".join(f.get("Architectures", [])),
            "package_type": f.get("PackageType", ""),
            "code_size_bytes": f.get("CodeSize", 0),
            "vpc_id": (f.get("VpcConfig") or {}).get("VpcId", "-"),
            "role": f.get("Role", "").split("/")[-1],
            "state": f.get("State", "Active"),
            "last_modified": f.get("LastModified", ""),
        })
    return {"lambda_functions": out}


def fmt_perm(p):
    proto = p.get("IpProtocol", "")
    proto = "ALL" if proto == "-1" else proto.upper()
    fp = p.get("FromPort")
    tp = p.get("ToPort")
    port_str = proto if fp is None else (f"{proto}:{fp}" if fp == tp else f"{proto}:{fp}-{tp}")
    sources = [r.get("CidrIp") for r in p.get("IpRanges", []) if r.get("CidrIp")]
    sources += [r.get("CidrIpv6") for r in p.get("Ipv6Ranges", []) if r.get("CidrIpv6")]
    sources += [g.get("GroupId") for g in p.get("UserIdGroupPairs", []) if g.get("GroupId")]
    src_str = ",".join(sources[:2]) + ("..." if len(sources) > 2 else "")
    return f"[{port_str} from {src_str}]"


def c_network(sess, cfg, region):
    ec2 = sess.client("ec2", config=cfg)
    res = {
        "vpcs": [],
        "subnets": [],
        "internet_gateways": [],
        "nat_gateways": [],
        "route_tables": [],
        "security_groups": []
    }

    # 1. VPCs
    for v in pages(ec2, "describe_vpcs", "Vpcs"):
        res["vpcs"].append({
            "id": v["VpcId"],
            "name": tname(v.get("Tags")),
            "cidr": v.get("CidrBlock", ""),
            "is_default": bool(v.get("IsDefault")),
            "state": v.get("State", ""),
            "dhcp": v.get("DhcpOptionsId", "-")
        })

    # 2. Route Tables & determine public subnets
    pub_subnets = set()
    for rtb in pages(ec2, "describe_route_tables", "RouteTables"):
        has_igw = any(r.get("GatewayId", "").startswith("igw-") for r in rtb.get("Routes", []))
        subnets = [a.get("SubnetId") for a in rtb.get("Associations", []) if a.get("SubnetId")]
        if has_igw:
            for s in subnets:
                pub_subnets.add(s)

        is_main = any(a.get("Main", False) for a in rtb.get("Associations", []))
        routes_summary = []
        default_target = "-"
        for r in rtb.get("Routes", []):
            dest = r.get("DestinationCidrBlock") or r.get("DestinationIpv6CidrBlock") or r.get("DestinationPrefixListId", "")
            target = (
                r.get("GatewayId") or r.get("NatGatewayId") or r.get("TransitGatewayId") or
                r.get("VpcPeeringConnectionId") or r.get("NetworkInterfaceId") or "local"
            )
            routes_summary.append(f"{dest}->{target}")
            if dest == "0.0.0.0/0":
                default_target = target

        res["route_tables"].append({
            "id": rtb["RouteTableId"],
            "name": tname(rtb.get("Tags")),
            "vpc_id": rtb.get("VpcId", "-"),
            "associated_subnets": subnets,
            "is_main": is_main,
            "default_gateway": default_target,
            "routes_summary": " | ".join(routes_summary[:4])
        })

    # 3. Subnets
    for s in pages(ec2, "describe_subnets", "Subnets"):
        sid = s["SubnetId"]
        is_pub = (sid in pub_subnets) or s.get("MapPublicIpOnLaunch", False)
        res["subnets"].append({
            "id": sid,
            "name": tname(s.get("Tags")),
            "vpc_id": s.get("VpcId", "-"),
            "cidr": s.get("CidrBlock", ""),
            "az": s.get("AvailabilityZone", ""),
            "type": "Public" if is_pub else "Private",
            "available_ips": s.get("AvailableIpAddressCount", 0),
            "state": s.get("State", "")
        })

    # 4. Internet Gateways
    for igw in pages(ec2, "describe_internet_gateways", "InternetGateways"):
        vpcs = [a.get("VpcId") for a in igw.get("Attachments", []) if a.get("VpcId")]
        res["internet_gateways"].append({
            "id": igw["InternetGatewayId"],
            "name": tname(igw.get("Tags")),
            "attached_vpcs": vpcs,
            "state": igw.get("Attachments", [{}])[0].get("State", "-") if igw.get("Attachments") else "-"
        })

    # 5. NAT Gateways
    for nat in pages(ec2, "describe_nat_gateways", "NatGateways"):
        if nat.get("State") == "deleted":
            continue
        eips = [a.get("PublicIp") for a in nat.get("NatGatewayAddresses", []) if a.get("PublicIp")]
        res["nat_gateways"].append({
            "id": nat["NatGatewayId"],
            "name": tname(nat.get("Tags")),
            "vpc_id": nat.get("VpcId", "-"),
            "subnet_id": nat.get("SubnetId", "-"),
            "state": nat.get("State", ""),
            "public_ips": eips
        })

    # 6. Security Groups
    for sg in pages(ec2, "describe_security_groups", "SecurityGroups"):
        inbounds = [fmt_perm(p) for p in sg.get("IpPermissions", [])]
        res["security_groups"].append({
            "id": sg["GroupId"],
            "name": tname(sg.get("Tags")) or sg.get("GroupName", ""),
            "group_name": sg.get("GroupName", ""),
            "vpc_id": sg.get("VpcId", "-"),
            "description": sg.get("Description", "-"),
            "inbound_rules_summary": " \n".join(inbounds) if inbounds else "No inbound rules",
            "inbound_rule_count": len(sg.get("IpPermissions", []))
        })

    return res


COLLECTORS = [
    ("ec2", c_ec2),
    ("rds", c_rds),
    ("elbv2", c_elbv2),
    ("s3", c_s3),
    ("lambda", c_lambda),
    ("network", c_network),
]


def resolve_region(cli_region):
    if cli_region:
        return cli_region
    for env in ("AWS_REGION", "AWS_DEFAULT_REGION"):
        if os.environ.get(env):
            return os.environ[env]
    try:
        r = boto3.Session().region_name
        if r:
            return r
    except Exception:
        pass
    return "ap-northeast-2"


def main():
    parser = argparse.ArgumentParser(description="AWS CloudShell read-only infra scanner")
    parser.add_argument("--region", help="Target region (defaults to CloudShell region)")
    parser.add_argument("--out", help="Output JSON path")
    args = parser.parse_args()

    region = resolve_region(args.region)
    print("=" * 65)
    print(f" [AWS CloudShell 인프라 스캐너 (v{SCHEMA_VERSION})]")
    print(f" - 대상 리전 : {region}")
    print(" - 보안 모드 : 세션 임시 자격증명 사용 (Zero pip install)")
    print("=" * 65)

    sess = boto3.Session(region_name=region)
    cfg = Config(retries={"mode": "adaptive", "max_attempts": 5})

    # 계정 및 Caller 정보
    account_id, caller_arn = "", ""
    try:
        sts = sess.client("sts", config=cfg)
        ident = sts.get_caller_identity()
        account_id = ident.get("Account", "")
        caller_arn = ident.get("Arn", "")
        print(f" - 계정 ID   : {account_id}")
        print(f" - 실행 역할 : {caller_arn}")
    except Exception as e:
        WARNINGS.append(f"sts: {e}")

    meta = {
        "schema_version": SCHEMA_VERSION,
        "scanned_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "region": region,
        "account_id": account_id,
        "caller_arn": caller_arn,
        "skipped": [],
        "errors": [],
        "warnings": WARNINGS,
    }

    resources = {
        "ec2_instances": [], "rds_instances": [], "load_balancers": [],
        "s3_buckets": [], "lambda_functions": [],
        "vpcs": [], "subnets": [], "internet_gateways": [],
        "nat_gateways": [], "route_tables": [], "security_groups": []
    }

    def run_col(item):
        name, fn = item
        print(f" [*] {name} 리소스 스캔 시작...")
        try:
            return name, fn(sess, cfg, region), None
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code in DENIED:
                return name, None, ("skipped", code)
            return name, None, ("error", f"{code}: {e}")
        except Exception as e:
            return name, None, ("error", str(e))

    with ThreadPoolExecutor(max_workers=6) as pool:
        for name, data, err in pool.map(run_col, COLLECTORS):
            if err:
                status, msg = err
                if status == "skipped":
                    print(f"  [!] {name}: 권한 부족({msg})으로 안전하게 건너뜁니다.")
                    meta["skipped"].append({"collector": name, "reason": msg})
                else:
                    print(f"  [!] {name} 오류: {msg}")
                    meta["errors"].append({"collector": name, "error": msg})
            elif data:
                for k, v in data.items():
                    if k in resources:
                        resources[k] = v
                print(f"  √ {name} 수집 완료")

    output_doc = {"meta": meta, "resources": resources}

    out_path = args.out or f"aws_spec_{region}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output_doc, f, ensure_ascii=False, indent=2)

    # 요약 출력
    counts = {k: len(v) for k, v in resources.items()}
    print("\n" + "=" * 65)
    print(f" [성공] 인프라 스캔 완료! ({out_path})")
    print(f" - VPC: {counts['vpcs']}개 | 서브넷: {counts['subnets']}개 | SG: {counts['security_groups']}개")
    print(f" - EC2: {counts['ec2_instances']}대 | RDS: {counts['rds_instances']}개 | ELB: {counts['load_balancers']}대")
    print(f" - S3: {counts['s3_buckets']}개 | Lambda: {counts['lambda_functions']}개")
    print("=" * 65)
    print("\n [CloudShell 파일 다운로드 방법]")
    print(" 1. AWS CloudShell 화면 우측 상단의 [Actions] 메뉴 클릭")
    print(" 2. [Download file] 선택")
    print(f" 3. 파일 경로에 아래 파일명을 입력하고 [Download]:")
    print(f"    {out_path}")
    print("\n 4. 다운로드한 JSON 파일을 로컬 브라우저 viewer.html에 Drag & Drop 하세요!")
    print("=" * 65)


if __name__ == "__main__":
    main()
