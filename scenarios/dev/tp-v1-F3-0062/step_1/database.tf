resource "aws_security_group" "sg_db" {
  description = "Database security group for tpl-32"
  name        = "sg_db-tpl-32"
  vpc_id      = aws_vpc.vpc_main.id

  ingress {
    from_port       = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.sg_app.id]
    to_port         = 5432
  }

  egress {
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = 0
    protocol    = "-1"
    to_port     = 0
  }

  ingress {
    from_port       = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.sg_db_peer.id]
    to_port         = 5432
  }
}

resource "aws_db_subnet_group" "dbsng_main" {
  name       = "dbsng_main-tpl-32"
  subnet_ids = [aws_subnet.sub_db[0].id, aws_subnet.sub_db[1].id, aws_subnet.sub_db[2].id]
}

resource "aws_db_instance" "rds_postgres" {
  allocated_storage      = 20
  db_subnet_group_name   = aws_db_subnet_group.dbsng_main.name
  engine                 = "postgres"
  identifier             = "rds-postgres-tpl-32"
  instance_class         = var.db_instance_class
  password               = var.db_password
  publicly_accessible    = false
  skip_final_snapshot    = true
  username               = "postgres"
  vpc_security_group_ids = [aws_security_group.sg_db.id]
}
