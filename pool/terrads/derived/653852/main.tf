terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.13.0"
    }
  }
}
 # Define provider region
 provider "aws" {
    region = "eu-west-3" # Paris
 }

# Create an EC2 instance
resource "aws_instance" "webapp_instance" {
    ami = var.instance_ami
    instance_type = var.instance_type
    tags = {
        "Name" = "WebAppInstance"
    }
}

#Define an AWS RDS database instance
resource "aws_db_instance" "database_instance" {
  allocated_storage    = var.db_allocated_storage
  db_name              = "mydb"
  storage_type         = "gp2"
  engine               = "mysql"
  engine_version       = var.db_engine_version
  instance_class       = "db.t3.micro"
  username             = "dbuser"
  password             = var.db_password 
  skip_final_snapshot = true
}

