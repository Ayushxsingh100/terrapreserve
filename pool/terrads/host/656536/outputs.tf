# RDS 모듈 출력 값들

output "db_instance_id" {
  description = "RDS 인스턴스 ID"
  value       = var.enable_rds ? aws_db_instance.main[0].id : null
}

output "db_instance_endpoint" {
  description = "RDS 인스턴스 엔드포인트"
  value       = var.enable_rds ? aws_db_instance.main[0].endpoint : null
}

output "db_instance_arn" {
  description = "RDS 인스턴스 ARN"
  value       = var.enable_rds ? aws_db_instance.main[0].arn : null
}

output "security_group_id" {
  description = "RDS 보안 그룹 ID"
  value       = aws_security_group.rds.id
}

output "instance_id" {
  description = "RDS 인스턴스 ID"
  value       = var.enable_rds ? aws_db_instance.main[0].id : null
}

output "endpoint" {
  description = "RDS 인스턴스 엔드포인트"
  value       = var.enable_rds ? aws_db_instance.main[0].endpoint : null
}

output "port" {
  description = "RDS 인스턴스 포트"
  value       = var.enable_rds ? aws_db_instance.main[0].port : null
}
