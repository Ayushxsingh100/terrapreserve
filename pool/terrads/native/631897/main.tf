# Security Groups
resource "aws_security_group" "api" {
  name        = "${var.project_name}-${var.environment}-sg-app"
  description = "Security Group for the API Go application"
  vpc_id      = var.vpc_id

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-sg-app"
  })
}

resource "aws_security_group" "rds" {
  name        = "${var.project_name}-${var.environment}-sg-db"
  description = "Security Group for the API Go RDS database"
  vpc_id      = var.vpc_id

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-sg-db"
  })
}

# Security Group Rules (separadas para evitar cycle)
resource "aws_security_group_rule" "api_ingress_http" {
  type              = "ingress"
  from_port         = 8000
  to_port           = 8000
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  description       = "API Go application port (EC2 and ALB)"
  security_group_id = aws_security_group.api.id
}

resource "aws_security_group_rule" "api_ingress_http_alb" {
  type                     = "ingress"
  from_port                = -1
  to_port                  = -1
  protocol                 = "-1"
  source_security_group_id = aws_security_group.rds.id
  description              = "DB application port RDS"
  security_group_id        = aws_security_group.api.id
}

resource "aws_security_group_rule" "api_ingress_ssh" {
  type              = "ingress"
  from_port         = 22
  to_port           = 22
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  description       = "SSH access"
  security_group_id = aws_security_group.api.id
}

resource "aws_security_group_rule" "api_egress_all" {
  type              = "egress"
  from_port         = -1
  to_port           = -1
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  description       = "All outbound traffic"
  security_group_id = aws_security_group.api.id
}

resource "aws_security_group_rule" "rds_ingress_postgres" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.api.id
  description              = "PostgreSQL from API"
  security_group_id        = aws_security_group.rds.id
}

# RDS Instance
resource "aws_db_instance" "main" {
  identifier = "${var.project_name}-${var.environment}-rds-main"

  # Engine Configuration
  engine            = "postgres"
  engine_version    = var.db_engine_version
  instance_class    = var.db_instance_class
  allocated_storage = var.db_allocated_storage
  storage_type      = "gp2"
  storage_encrypted = true

  # Database Configuration
  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  # Network Configuration
  vpc_security_group_ids = [aws_security_group.rds.id]
  # Usar subnet group padrão da VPC ao invés de criar um customizado
  publicly_accessible = false

  # Backup Configuration - TOTALMENTE DESABILITADO
  backup_retention_period = 0
  backup_window           = null
  maintenance_window      = "Sun:04:00-Sun:05:00"

  # Monitoring - DESABILITADO
  performance_insights_enabled = false
  monitoring_interval          = 0

  # High Availability - DESABILITADO
  multi_az = false

  # Deletion Protection - TOTALMENTE DESABILITADO
  deletion_protection       = false
  skip_final_snapshot       = true
  final_snapshot_identifier = null
  delete_automated_backups  = true

  tags = merge(var.tags, {
    Name  = "${var.project_name}-${var.environment}-rds-main"
    Owner = "Gabriel"
  })
}

# EC2 Instance
resource "aws_instance" "bastion" {
  ami           = var.ami_id
  instance_type = var.instance_type
  key_name      = var.key_name

  # Network Configuration
  subnet_id                   = var.subnet_ids[0] # Primeira subnet da lista (que funciona)
  vpc_security_group_ids      = [aws_security_group.api.id]
  associate_public_ip_address = true

  # No user_data needed - GitHub Actions workflow handles all deployment
  # The EC2.yml workflow will:
  # 1. SSH into the instance
  # 2. Deploy the Go binary
  # 3. Set environment variables
  # 4. Start the application

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-ec2-bastion"
  })

  depends_on = [aws_db_instance.main]
}
