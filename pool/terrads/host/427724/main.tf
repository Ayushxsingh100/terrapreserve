resource "aws_db_instance" "this" {
  identifier_prefix      = var.identifier_prefix
  engine                 = var.engine
  allocated_storage      = var.storage
  instance_class         = var.instance_class
  db_name                = var.db_name
  username               = var.db_username
  password               = var.db_password
  skip_final_snapshot    = true
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible    = false
  db_subnet_group_name   = aws_db_subnet_group.this.name
  availability_zone      = var.availability_zone
}
resource "aws_db_subnet_group" "this" {
  name       = var.identifier_prefix
  subnet_ids = [var.private_subnet_ids[0], var.private_subnet_ids[1]]
}
