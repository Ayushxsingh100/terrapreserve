# ============================================================
# Security Group 모듈 입력 변수 정의
# 보안 그룹 생성에 필요한 변수들
# ============================================================

# 보안 그룹이 속할 VPC ID
variable "vpc_id" {
  description = "보안 그룹을 생성할 VPC의 ID"
  type        = string
}

# 리전 식별 이름 (리소스 태그에 사용)
variable "region_name" {
  description = "리전 이름 (보안 그룹 명명에 사용)"
  type        = string
}

# ------------------------------------------------------------
# 보안 그룹 설정 맵
# 여러 보안 그룹과 각각의 인바운드/아웃바운드 규칙을 정의
# ------------------------------------------------------------
variable "sg" {
  description = "보안 그룹 설정 맵 (그룹별 인바운드/아웃바운드 규칙)"
  type = map(object({
    # 인바운드 규칙 맵 (규칙 이름 → 규칙 상세)
    ingress_rules = map(object({
      protocol    : string        # 프로토콜 (tcp/udp/icmp/-1)
      from_port   : number        # 시작 포트
      to_port     : number        # 종료 포트
      cidr_blocks : list(string)  # 허용 CIDR 블록 목록
    }))
    
    # 아웃바운드 규칙 맵 (규칙 이름 → 규칙 상세)
    egress_rules = map(object({
      protocol    : string        # 프로토콜
      from_port   : number        # 시작 포트
      to_port     : number        # 종료 포트
      cidr_blocks : list(string)  # 허용 CIDR 블록 목록
    }))
  }))
}
