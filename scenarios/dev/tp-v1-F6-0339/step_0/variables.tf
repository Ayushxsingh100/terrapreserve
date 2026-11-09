# RDS 모듈 변수 정의

variable "project_name" {
  description = "프로젝트 이름"
  type        = string
}

variable "environment" {
  description = "환경 (production, development)"
  type        = string
}

variable "enable_rds" {
  description = "RDS 활성화"
  type        = bool
  default     = false
}

variable "private_subnet_ids" {
  description = "프라이빗 서브넷 ID 목록"
  type        = list(string)
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "db_security_group_id" {
  description = "데이터베이스 보안 그룹 ID"
  type        = string
  default     = ""
}

variable "db_engine" {
  description = "데이터베이스 엔진"
  type        = string
  default     = "postgres"
}

variable "db_engine_version" {
  description = "데이터베이스 엔진 버전"
  type        = string
  default     = "14.9"
}

variable "db_instance_class" {
  description = "데이터베이스 인스턴스 클래스"
  type        = string
  default     = "db.t3.micro"
}

variable "db_allocated_storage" {
  description = "할당된 스토리지 (GB)"
  type        = number
  default     = 20
}

variable "db_max_allocated_storage" {
  description = "최대 할당 스토리지 (GB)"
  type        = number
  default     = 100
}

variable "db_storage_type" {
  description = "스토리지 타입"
  type        = string
  default     = "gp2"
}

variable "db_name" {
  description = "데이터베이스 이름"
  type        = string
  default     = "enterprise_rag"
}

variable "db_username" {
  description = "데이터베이스 사용자명"
  type        = string
  default     = "postgres"
}

variable "db_password" {
  description = "데이터베이스 비밀번호"
  type        = string
  sensitive   = true
}

variable "db_backup_retention_period" {
  description = "백업 보존 기간 (일)"
  type        = number
  default     = 7
}

variable "db_backup_window" {
  description = "백업 윈도우"
  type        = string
  default     = "03:00-04:00"
}

variable "db_maintenance_window" {
  description = "유지보수 윈도우"
  type        = string
  default     = "sun:04:00-sun:05:00"
}

variable "db_skip_final_snapshot" {
  description = "최종 스냅샷 건너뛰기"
  type        = bool
  default     = true
}

variable "db_deletion_protection" {
  description = "삭제 보호"
  type        = bool
  default     = false
}

variable "kms_key_id" {
  description = "KMS 키 ID (암호화용)"
  type        = string
  default     = ""
}

variable "common_tags" {
  description = "공통 태그"
  type        = map(string)
  default     = {}
}
