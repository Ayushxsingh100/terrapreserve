provider "aws" {
  region = "us-east-1"
}

resource "aws_instance" "academia_ec2" {
  ami           = "ami-053b0d53c279acc90"  # Ubuntu 22.04 us-east-1
  instance_type = "t2.small"

  tags = {
    Name = "AcademiaCorpoEmForma"
  }
}


resource "aws_db_instance" "academia_rds" {
  identifier              = "academia-db"
  allocated_storage       = 20
  engine                  = "postgres"
  instance_class          = "db.t3.micro"
  db_name                 = "academia_db"
  username                = "usuario_aqui"
  password                = var.db_password
  publicly_accessible     = true
  skip_final_snapshot     = true
}











