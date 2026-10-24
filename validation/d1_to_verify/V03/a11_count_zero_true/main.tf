resource "aws_db_instance" "d" {
  engine              = "postgres"
  instance_class      = "db.t3.micro"
  allocated_storage   = 20
  count               = 0
  publicly_accessible = true
}
