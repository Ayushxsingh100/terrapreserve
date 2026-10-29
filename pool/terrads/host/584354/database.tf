
resource "aws_db_instance" "tech-challenge-rds" {
  identifier               = "tech-challenge-rds-tf"
  allocated_storage        = 20
  max_allocated_storage    = 100
  engine                   = "postgres"
  engine_version           = "16.3"
  instance_class           = "db.t4g.micro"
  username                 = var.postgres_user
  password                 = var.postgres_password
  parameter_group_name     = "default.postgres16"
  skip_final_snapshot      = true
  publicly_accessible      = true
  backup_retention_period  = 7
  delete_automated_backups = true

  vpc_security_group_ids = [aws_security_group.database_security_group.id]
  tags = {
    Name = "tech-challenge-rds"
  }
}