# V07: what does the plan show for aws_db_instance.port when it is unset, literal, or variable-driven?
provider "aws" {
  region = "us-east-1"

  skip_credentials_validation = true
  skip_requesting_account_id  = true
  skip_metadata_api_check     = true
  skip_region_validation      = true
}

variable "db_port" {
  type    = number
  default = 5432
}

resource "aws_db_instance" "unset_postgres" {
  identifier                  = "unset-postgres"
  engine                      = "postgres"
  instance_class              = "db.t3.micro"
  allocated_storage           = 20
  username                    = "tpadmin"
  manage_master_user_password = true
  skip_final_snapshot         = true
}

resource "aws_db_instance" "unset_mysql" {
  identifier                  = "unset-mysql"
  engine                      = "mysql"
  instance_class              = "db.t3.micro"
  allocated_storage           = 20
  username                    = "tpadmin"
  manage_master_user_password = true
  skip_final_snapshot         = true
}

resource "aws_db_instance" "literal_5432" {
  identifier                  = "literal-5432"
  engine                      = "postgres"
  instance_class              = "db.t3.micro"
  allocated_storage           = 20
  username                    = "tpadmin"
  manage_master_user_password = true
  skip_final_snapshot         = true
  port                        = 5432
}

resource "aws_db_instance" "literal_3306" {
  identifier                  = "literal-3306"
  engine                      = "postgres"
  instance_class              = "db.t3.micro"
  allocated_storage           = 20
  username                    = "tpadmin"
  manage_master_user_password = true
  skip_final_snapshot         = true
  port                        = 3306
}

resource "aws_db_instance" "from_variable" {
  identifier                  = "from-variable"
  engine                      = "postgres"
  instance_class              = "db.t3.micro"
  allocated_storage           = 20
  username                    = "tpadmin"
  manage_master_user_password = true
  skip_final_snapshot         = true
  port                        = var.db_port
}
