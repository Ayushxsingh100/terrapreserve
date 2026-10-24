variable "public" {
  type = bool
}

resource "aws_db_instance" "d" {
  engine              = "postgres"
  instance_class      = "db.t3.micro"
  allocated_storage   = 20
  publicly_accessible = var.public
}
