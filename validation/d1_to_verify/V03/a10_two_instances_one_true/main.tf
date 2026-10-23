resource "aws_db_instance" "d1" {
  engine              = "postgres"
  instance_class      = "db.t3.micro"
  allocated_storage   = 20
  publicly_accessible = false
}

resource "aws_db_instance" "d2" {
  engine              = "postgres"
  instance_class      = "db.t3.micro"
  allocated_storage   = 20
  publicly_accessible = true
}
