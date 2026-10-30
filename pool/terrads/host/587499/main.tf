resource "aws_db_subnet_group" "this" {
  name       = "${var.db_instance_identifier}-subnet-group"
  subnet_ids = var.subnets

  tags = {
    Name = "${var.db_instance_identifier}-subnet-group"
  }
}

resource "aws_security_group" "this" {
  name        = "${var.db_instance_identifier}-sg"
  description = "Security group for RDS"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = var.port
    to_port         = var.port
    protocol        = "tcp"
    security_groups = var.allowed_security_groups
  }

  egress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_instance" "this" {
  identifier           = var.db_instance_identifier
  engine               = var.engine
  engine_version       = var.engine_version
  instance_class       = var.instance_class
  allocated_storage    = var.allocated_storage
  db_name              = var.db_name
  username             = var.username
  password             = var.password
  port                 = var.port
  vpc_security_group_ids = [aws_security_group.this.id]
  db_subnet_group_name = aws_db_subnet_group.this.name
  skip_final_snapshot  = true
  publicly_accessible  = false

  tags = {
    Name = var.db_instance_identifier
  }
}
