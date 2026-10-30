# ============================================================
# Security Group 모듈
# 프로젝트 목적: AWS 방화벽 규칙 관리 (인바운드/아웃바운드 트래픽 제어)
# 학습 목표: Security Group을 통한 네트워크 보안 설정 이해
# ============================================================

# ------------------------------------------------------------
# Security Group 리소스
# 역할: VPC 내 리소스에 대한 인바운드/아웃바운드 트래픽 제어
# 학습 포인트: for_each와 dynamic 블록을 사용한 동적 규칙 생성
# ------------------------------------------------------------
resource "aws_security_group" "sg" {
  # 보안 그룹 맵의 각 항목에 대해 보안 그룹 생성
  # 예: web, rds, dns, lb 등 여러 보안 그룹을 한 번에 생성
  for_each = var.sg
  
  # 이 보안 그룹이 속할 VPC
  vpc_id = var.vpc_id
  
  # 보안 그룹 이름: 리전명-용도 형태로 명명
  name   = "${var.region_name}-sg-js-${each.key}"

  # ------------------------------------------------------------
  # 인바운드 규칙 (Ingress Rules) - 동적 블록
  # 역할: 외부에서 리소스로 들어오는 트래픽 허용 규칙
  # 학습 포인트: dynamic 블록을 통한 반복 규칙 생성
  # ------------------------------------------------------------
  dynamic "ingress" {
    # 해당 보안 그룹의 인바운드 규칙들을 순회
    for_each = each.value.ingress_rules
    content {
      # 프로토콜: tcp, udp, icmp, -1(모두)
      protocol = ingress.value.protocol
      
      # 포트 범위 시작
      from_port = ingress.value.from_port
      
      # 포트 범위 끝 (단일 포트면 from_port와 동일)
      to_port = ingress.value.to_port
      
      # 허용할 소스 CIDR 블록
      # 0.0.0.0/0: 모든 IP 허용, 10.0.0.0/8: 특정 대역만 허용
      cidr_blocks = ingress.value.cidr_blocks
    }
  }
  
  tags = {
    Name = "${var.region_name}-sg-js-${each.key}"
  }

  # ------------------------------------------------------------
  # 아웃바운드 규칙 (Egress Rules) - 동적 블록
  # 역할: 리소스에서 외부로 나가는 트래픽 허용 규칙
  # 학습 포인트: 아웃바운드 규칙도 동적으로 생성 가능
  # ------------------------------------------------------------
  dynamic "egress" {
    # 해당 보안 그룹의 아웃바운드 규칙들을 순회
    for_each = each.value.egress_rules
    content {
      # 프로토콜
      protocol = egress.value.protocol
      
      # 포트 범위
      from_port = egress.value.from_port
      to_port   = egress.value.to_port
      
      # 허용할 목적지 CIDR 블록
      cidr_blocks = egress.value.cidr_blocks
    }
  }
}
