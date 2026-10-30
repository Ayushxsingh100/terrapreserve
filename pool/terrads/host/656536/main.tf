# RDS 모듈 - 관계형 데이터베이스 구성

# RDS 보안 그룹
resource "aws_security_group" "rds" {
  name_prefix = "${var.project_name}-${var.environment}-rds-"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]  # VPC 내부에서만 접근
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.common_tags, {
    Name = "${var.project_name}-${var.environment}-rds-sg"
  })
}

# RDS 서브넷 그룹
resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-${var.environment}-db-subnet-group-${formatdate("YYYYMMDDHHmm", timestamp())}"
  subnet_ids = var.private_subnet_ids

  tags = {
    Name        = "${var.project_name}-${var.environment}-db-subnet-group-${formatdate("YYYYMMDDHHmm", timestamp())}"
    Environment = var.environment
    Project     = var.project_name
  }
}

# RDS 인스턴스
resource "aws_db_instance" "main" {
  count = var.enable_rds ? 1 : 0

  identifier = "${var.project_name}-${var.environment}-rds"

  engine         = var.db_engine
  engine_version = var.db_engine_version
  instance_class = var.db_instance_class

  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = var.db_max_allocated_storage
  storage_type          = var.db_storage_type
  storage_encrypted     = true

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  vpc_security_group_ids = var.db_security_group_id != "" ? [var.db_security_group_id] : [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name

  backup_retention_period = var.db_backup_retention_period
  backup_window          = var.db_backup_window
  maintenance_window     = var.db_maintenance_window

  skip_final_snapshot = var.db_skip_final_snapshot
  deletion_protection = var.db_deletion_protection

  tags = {
    Name        = "${var.project_name}-${var.environment}-rds"
    Environment = var.environment
    Project     = var.project_name
  }
}
