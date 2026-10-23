# V05: what does the plan show for aws_db_instance.publicly_accessible?
provider "aws" {
  region = "us-east-1"

  skip_credentials_validation = true
  skip_requesting_account_id  = true
  skip_metadata_api_check     = true
  skip_region_validation      = true
}

variable "public" {
  type    = bool
  default = true
}

resource "aws_db_instance" "unset" {
  identifier                  = "unset"
  engine                      = "postgres"
  instance_class              = "db.t3.micro"
  allocated_storage           = 20
  username                    = "tpadmin"
  manage_master_user_password = true
  skip_final_snapshot         = true
}

resource "aws_db_instance" "explicit_false" {
  identifier                  = "explicit-false"
  engine                      = "postgres"
  instance_class              = "db.t3.micro"
  allocated_storage           = 20
  username                    = "tpadmin"
  manage_master_user_password = true
  skip_final_snapshot         = true
  publicly_accessible         = false
}

resource "aws_db_instance" "explicit_true" {
  identifier                  = "explicit-true"
  engine                      = "postgres"
  instance_class              = "db.t3.micro"
  allocated_storage           = 20
  username                    = "tpadmin"
  manage_master_user_password = true
  skip_final_snapshot         = true
  publicly_accessible         = true
}

resource "aws_db_instance" "from_variable" {
  identifier                  = "from-variable"
  engine                      = "postgres"
  instance_class              = "db.t3.micro"
  allocated_storage           = 20
  username                    = "tpadmin"
  manage_master_user_password = true
  skip_final_snapshot         = true
  publicly_accessible         = var.public
}
