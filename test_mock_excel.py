"""
Mock test to verify Excel generation with realistic customer AWS infrastructure data.
"""

from excel_generator import ExcelReportBuilder

dummy_data = {
    "metadata": {
        "region": "ap-northeast-2",
        "scanned_at": "2026-10-25 15:30:00"
    },
    "summary": {
        "vpc_count": 2,
        "subnet_count": 6,
        "igw_count": 1,
        "nat_count": 2,
        "sg_count": 4,
        "ec2_count": 3,
        "rds_count": 2,
        "elb_count": 1,
        "s3_count": 3,
        "lambda_count": 2
    },
    "vpcs": [
        {"name": "prd-vpc-main", "vpc_id": "vpc-0a1b2c3d4e5f6001", "cidr": "10.0.0.0/16", "is_default": "아니오 (사용자 생성)", "state": "available", "dhcp": "dopt-012345"},
        {"name": "default", "vpc_id": "vpc-0a1b2c3d4e5f6002", "cidr": "172.31.0.0/16", "is_default": "예 (기본)", "state": "available", "dhcp": "dopt-012345"}
    ],
    "subnets": [
        {"name": "prd-pub-sub-2a", "subnet_id": "subnet-01a2b3c4d5001", "vpc_id": "vpc-0a1b2c3d4e5f6001", "cidr": "10.0.1.0/24", "az": "ap-northeast-2a", "type": "Public", "available_ips": 250, "state": "available"},
        {"name": "prd-pub-sub-2c", "subnet_id": "subnet-01a2b3c4d5002", "vpc_id": "vpc-0a1b2c3d4e5f6001", "cidr": "10.0.2.0/24", "az": "ap-northeast-2c", "type": "Public", "available_ips": 251, "state": "available"},
        {"name": "prd-app-sub-2a", "subnet_id": "subnet-01a2b3c4d5003", "vpc_id": "vpc-0a1b2c3d4e5f6001", "cidr": "10.0.11.0/24", "az": "ap-northeast-2a", "type": "Private", "available_ips": 249, "state": "available"},
        {"name": "prd-app-sub-2c", "subnet_id": "subnet-01a2b3c4d5004", "vpc_id": "vpc-0a1b2c3d4e5f6001", "cidr": "10.0.12.0/24", "az": "ap-northeast-2c", "type": "Private", "available_ips": 250, "state": "available"},
        {"name": "prd-db-sub-2a", "subnet_id": "subnet-01a2b3c4d5005", "vpc_id": "vpc-0a1b2c3d4e5f6001", "cidr": "10.0.21.0/24", "az": "ap-northeast-2a", "type": "Private", "available_ips": 251, "state": "available"},
        {"name": "prd-db-sub-2c", "subnet_id": "subnet-01a2b3c4d5006", "vpc_id": "vpc-0a1b2c3d4e5f6001", "cidr": "10.0.22.0/24", "az": "ap-northeast-2c", "type": "Private", "available_ips": 251, "state": "available"}
    ],
    "gateways": {
        "igw": [
            {"name": "prd-igw", "igw_id": "igw-0987654321fedcba", "attached_vpc": "vpc-0a1b2c3d4e5f6001", "state": "attached"}
        ],
        "nat": [
            {"name": "prd-nat-2a", "nat_id": "nat-0112233445566778", "vpc_id": "vpc-0a1b2c3d4e5f6001", "subnet_id": "subnet-01a2b3c4d5001", "state": "available", "public_ip": "43.201.10.55"},
            {"name": "prd-nat-2c", "nat_id": "nat-0998877665544332", "vpc_id": "vpc-0a1b2c3d4e5f6001", "subnet_id": "subnet-01a2b3c4d5002", "state": "available", "public_ip": "43.201.20.77"}
        ]
    },
    "route_tables": [
        {"name": "prd-pub-rtb", "rtb_id": "rtb-0123456789abcdef", "vpc_id": "vpc-0a1b2c3d4e5f6001", "associated_subnets": "subnet-01a2b3c4d5001, subnet-01a2b3c4d5002", "default_gateway": "igw-0987654321fedcba", "routes_summary": "10.0.0.0/16 -> local | 0.0.0.0/0 -> igw-0987654321fedcba"},
        {"name": "prd-pri-rtb-2a", "rtb_id": "rtb-0fedcba987654321", "vpc_id": "vpc-0a1b2c3d4e5f6001", "associated_subnets": "subnet-01a2b3c4d5003, subnet-01a2b3c4d5005", "default_gateway": "nat-0112233445566778", "routes_summary": "10.0.0.0/16 -> local | 0.0.0.0/0 -> nat-0112233445566778"}
    ],
    "security_groups": [
        {"name": "prd-alb-sg", "group_id": "sg-0102030405060708", "group_name": "prd-alb-sg", "vpc_id": "vpc-0a1b2c3d4e5f6001", "description": "ALB 외부 허용 보안그룹", "inbound_rules": "[tcp:80 from 0.0.0.0/0] \n[tcp:443 from 0.0.0.0/0]", "inbound_rule_count": 2},
        {"name": "prd-was-sg", "group_id": "sg-0203040506070809", "group_name": "prd-was-sg", "vpc_id": "vpc-0a1b2c3d4e5f6001", "description": "WAS 내부 허용 보안그룹", "inbound_rules": "[tcp:8080 from sg-0102030405060708] \n[tcp:22 from 10.0.0.0/16]", "inbound_rule_count": 2},
        {"name": "prd-db-sg", "group_id": "sg-0304050607080910", "group_name": "prd-db-sg", "vpc_id": "vpc-0a1b2c3d4e5f6001", "description": "Aurora MySQL DB 보안그룹", "inbound_rules": "[tcp:3306 from sg-0203040506070809]", "inbound_rule_count": 1}
    ],
    "ec2_instances": [
        {"name": "prd-was-01", "instance_id": "i-0123456789abcdef0", "state": "running", "instance_type": "m6i.large", "vcpu": 2, "ram_gib": 8, "private_ip": "10.0.11.20", "public_ip": "-", "vpc_id": "vpc-0a1b2c3d4e5f6001", "subnet_id": "subnet-01a2b3c4d5003", "az": "ap-northeast-2a", "key_name": "prd-keypair", "launch_time": "2026-10-20 09:00"},
        {"name": "prd-was-02", "instance_id": "i-0123456789abcdef1", "state": "running", "instance_type": "m6i.large", "vcpu": 2, "ram_gib": 8, "private_ip": "10.0.12.35", "public_ip": "-", "vpc_id": "vpc-0a1b2c3d4e5f6001", "subnet_id": "subnet-01a2b3c4d5004", "az": "ap-northeast-2c", "key_name": "prd-keypair", "launch_time": "2026-10-20 09:05"},
        {"name": "prd-bastion", "instance_id": "i-0987654321fedcba0", "state": "stopped", "instance_type": "t3.micro", "vcpu": 2, "ram_gib": 1, "private_ip": "10.0.1.100", "public_ip": "43.201.99.12", "vpc_id": "vpc-0a1b2c3d4e5f6001", "subnet_id": "subnet-01a2b3c4d5001", "az": "ap-northeast-2a", "key_name": "bastion-keypair", "launch_time": "2026-10-15 14:00"}
    ],
    "rds_instances": [
        {"db_id": "prd-mysql-cluster-writer", "status": "available", "engine": "aurora-mysql 8.0.mysql_aurora.3.04.0", "db_class": "db.r6g.large", "storage": "100 GB (aurora)", "multi_az": "예 (Multi-AZ)", "endpoint": "prd-mysql-cluster.cluster-xyz.ap-northeast-2.rds.amazonaws.com:3306", "vpc_id": "vpc-0a1b2c3d4e5f6001", "subnet_group": "prd-db-subnet-group"},
        {"db_id": "prd-mysql-cluster-reader", "status": "available", "engine": "aurora-mysql 8.0.mysql_aurora.3.04.0", "db_class": "db.r6g.large", "storage": "100 GB (aurora)", "multi_az": "예 (Multi-AZ)", "endpoint": "prd-mysql-cluster.cluster-ro-xyz.ap-northeast-2.rds.amazonaws.com:3306", "vpc_id": "vpc-0a1b2c3d4e5f6001", "subnet_group": "prd-db-subnet-group"}
    ],
    "load_balancers": [
        {"name": "prd-external-alb", "type": "APPLICATION", "scheme": "인터넷 연결(internet-facing)", "state": "active", "dns_name": "prd-external-alb-123456789.ap-northeast-2.elb.amazonaws.com", "vpc_id": "vpc-0a1b2c3d4e5f6001", "listeners": "HTTP:80, HTTPS:443"}
    ],
    "s3_buckets": [
        {"name": "prd-customer-static-web", "region": "ap-northeast-2", "is_current_region": "예", "created_at": "2026-10-10 11:20"},
        {"name": "prd-customer-app-backup", "region": "ap-northeast-2", "is_current_region": "예", "created_at": "2026-10-12 16:45"},
        {"name": "prd-customer-access-logs", "region": "ap-northeast-2", "is_current_region": "예", "created_at": "2026-10-12 17:00"}
    ],
    "lambda_functions": [
        {"name": "prd-image-thumbnailer", "runtime": "python3.11", "memory": "512 MB", "timeout": "30 초", "handler": "lambda_function.lambda_handler", "last_modified": "2026-10-21 18:22:10"},
        {"name": "prd-nightly-batch-trigger", "runtime": "nodejs18.x", "memory": "256 MB", "timeout": "60 초", "handler": "index.handler", "last_modified": "2026-10-22 02:00:15"}
    ]
}

if __name__ == "__main__":
    builder = ExcelReportBuilder(dummy_data, customer_name="(주)한국엔터프라이즈")
    filename = "test_AWS_인프라_생성명세서.xlsx"
    builder.save_to_file(filename)
    print(f"Successfully generated: {filename}")
