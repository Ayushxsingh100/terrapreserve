# MAIN.TF FOR RDS MODULE

locals {
  app_name             = "${var.vpc_namespace}-rds"
  vpc_id               = var.vpc_id
  rds_port             = var.rds_port
  rds_cidr_blocks      = [var.vpc_cidr]
  db_name              = var.db_name
  db_username          = var.db_username
  db_password          = var.db_password
  db_subnet_group_name = var.db_subnet_group_name
  private_subnets      = var.private_subnets
  region               = var.region
  instance_class       = var.instance_class # if none provided the default one is "db.t2.micro" ( REQUIRED)

  common_tags = {
    Environment = "dev"
    Project     = "${local.app_name}-using-EFS"
  }
}

# Create RDS Security Group and ingress and egress rules
# https://www.terraform.io/docs/providers/aws/r/security_group.html

resource "aws_security_group" "this" {
  name   = "${local.app_name}-SG"
  vpc_id = local.vpc_id

  tags = {
    Name = "${local.app_name}-SG"
  }
}

resource "aws_security_group_rule" "ingress" {
  type              = "ingress"
  from_port         = local.rds_port
  to_port           = local.rds_port
  protocol          = "TCP"
  cidr_blocks       = local.rds_cidr_blocks
  security_group_id = aws_security_group.this.id
}

resource "aws_security_group_rule" "egress" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.this.id
}

resource "aws_db_subnet_group" "this" {
  name        = local.db_subnet_group_name
  subnet_ids  = local.private_subnets
  description = "database subnet group for wordpress fargate rds cluster"

  tags = {
    Name = "${local.app_name}-db-SubnetGroup"
  }
}

resource "aws_db_instance" "this" {
  identifier           = "${local.app_name}-db" # the DB cluster identifier 
  storage_type         = "gp2"                  # (optional) under storate the Storage type General Purpose (SSD), if omitted it automatically put the latest
  allocated_storage    = 20                     # under storage the allocated storage text box - Required unless a snapshot_identifer  or replicate_source is provided
  engine               = "mysql"
  engine_version       = "8.0"                # it would get the latest (OPTIONAL) 
  instance_class       = local.instance_class # it is in the free tier "db.t2.micro" ( REQUIRED)
  port                 = local.rds_port       # ( OPTIONAL) Once terraform knows it is "mysql" it knows what port to put. Port on which the DB accepts connections
  db_subnet_group_name = aws_db_subnet_group.this.name
  db_name              = local.db_name # the name of the database when the instance is created
  # Required unless a snapshot_identifier or replicate_source_db is provided - Username for the master user
  username = local.db_username
  # Required unless a snapshot_identifier or replicate_source_db is provided - Password for the master user
  password = local.db_password
  # every time you create a database a parameter group is created but you dont see it
  parameter_group_name   = "default.mysql8.0" # Optional - the name of the DB parameter group
  availability_zone      = "${local.region}a" # Optional - if not specified terraform will choose it for you
  publicly_accessible    = false              # Optional - by default is false - not publicly accesible
  deletion_protection    = false              # Optional - If true it wont delete unless deletion protections is not enable -default value is false
  skip_final_snapshot    = true               # Optional - If true it skips the final snapshot before the database is deleted -default value is true
  vpc_security_group_ids = [aws_security_group.this.id]

  tags = {
    Name = "${local.app_name}-DB"
  }
}
