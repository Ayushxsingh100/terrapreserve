resource "aws_vpc" "vpc_main" {
  cidr_block           = "10.195.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
}

resource "aws_internet_gateway" "igw_main" {
  vpc_id = aws_vpc.vpc_main.id
}

resource "aws_subnet" "sub_app" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.195.1.0/24"
  vpc_id            = aws_vpc.vpc_main.id
}

resource "aws_subnet" "sub_db" {
  count = 2

  availability_zone = ["us-east-1a", "us-east-1b"][count.index]
  cidr_block        = ["10.195.10.0/24", "10.195.11.0/24"][count.index]
  vpc_id            = aws_vpc.vpc_main.id
}

resource "aws_subnet" "sub_app_spare" {
  availability_zone = "us-east-1b"
  cidr_block        = "10.195.200.0/24"
  vpc_id            = aws_vpc.vpc_main.id
}

resource "aws_route_table" "rt_public_a" {
  vpc_id = aws_vpc.vpc_main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw_main.id
  }
}

resource "aws_route_table_association" "rta_app" {
  route_table_id = aws_route_table.rt_public_a.id
  subnet_id      = aws_subnet.sub_app.id
}

resource "aws_route_table" "rt_db" {
  count = 2

  vpc_id = aws_vpc.vpc_main.id
}

resource "aws_route_table_association" "rta_db" {
  count = 2

  route_table_id = aws_route_table.rt_db[count.index].id
  subnet_id      = aws_subnet.sub_db[count.index].id
}

resource "aws_security_group_rule" "sg_db_from_app_5432" {
  from_port                = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.sg_db.id
  source_security_group_id = aws_security_group.sg_app.id
  to_port                  = 5432
  type                     = "ingress"
}

resource "aws_security_group_rule" "sg_db_egress" {
  cidr_blocks       = ["0.0.0.0/0"]
  from_port         = 0
  protocol          = "-1"
  security_group_id = aws_security_group.sg_db.id
  to_port           = 0
  type              = "egress"
}

resource "aws_security_group_rule" "sg_app_egress" {
  cidr_blocks       = ["0.0.0.0/0"]
  from_port         = 0
  protocol          = "-1"
  security_group_id = aws_security_group.sg_app.id
  to_port           = 0
  type              = "egress"
}

resource "aws_security_group" "sg_app" {
  description = "Application security group for tpl-23"
  name        = "sg_app-tpl-23"
  vpc_id      = aws_vpc.vpc_main.id
}

resource "aws_security_group" "sg_db" {
  description = "Database security group for tpl-23"
  name        = "sg_db-tpl-23"
  vpc_id      = aws_vpc.vpc_main.id
}

resource "aws_instance" "ec2_app" {
  ami                    = "ami-0c55b159cbfafe1f0"
  instance_type          = "t3.nano"
  subnet_id              = aws_subnet.sub_app.id
  vpc_security_group_ids = [aws_security_group.sg_app.id, aws_security_group.monitoring_sg.id]
}

resource "aws_db_subnet_group" "dbsng_main" {
  name       = "dbsng_main-tpl-23"
  subnet_ids = [aws_subnet.sub_db[0].id, aws_subnet.sub_db[1].id]
}

resource "aws_db_instance" "rds_postgres" {
  allocated_storage      = 20
  db_subnet_group_name   = aws_db_subnet_group.dbsng_main.name
  engine                 = "postgres"
  identifier             = "rds-postgres-tpl-23"
  instance_class         = "db.t3.micro"
  password               = var.db_password
  publicly_accessible    = false
  skip_final_snapshot    = true
  username               = "postgres"
  vpc_security_group_ids = [aws_security_group.sg_db.id]
}

resource "aws_security_group" "monitoring_sg" {
  description = "Monitoring security group"
  name        = "monitoring_sg-mon"
  vpc_id      = aws_vpc.vpc_main.id
}
