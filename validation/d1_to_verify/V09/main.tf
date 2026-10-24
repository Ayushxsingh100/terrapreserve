# V09: protocol spellings in both rule forms. Every value is a separate resource so that one rejected
# value does not hide the others. Values: TCP tcp Tcp ALL All all -1 6 ICMP UDP icmpv6 ICMPV6 58 17.

provider "aws" {
  region = "us-east-1"

  skip_credentials_validation = true
  skip_requesting_account_id  = true
  skip_metadata_api_check     = true
  skip_region_validation      = true
}

resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
}

resource "aws_security_group" "rules" {
  name   = "rules"
  vpc_id = aws_vpc.main.id
}

resource "aws_security_group_rule" "p01" {
  type              = "ingress"
  security_group_id = aws_security_group.rules.id
  protocol          = "TCP"
  from_port         = 22
  to_port           = 22
  cidr_blocks       = ["10.0.0.0/24"]
}

resource "aws_security_group" "p01" {
  name   = "p01"
  vpc_id = aws_vpc.main.id

  ingress {
    protocol    = "TCP"
    from_port   = 22
    to_port     = 22
    cidr_blocks = ["10.0.0.0/24"]
  }
}

resource "aws_security_group_rule" "p02" {
  type              = "ingress"
  security_group_id = aws_security_group.rules.id
  protocol          = "tcp"
  from_port         = 22
  to_port           = 22
  cidr_blocks       = ["10.0.0.0/24"]
}

resource "aws_security_group" "p02" {
  name   = "p02"
  vpc_id = aws_vpc.main.id

  ingress {
    protocol    = "tcp"
    from_port   = 22
    to_port     = 22
    cidr_blocks = ["10.0.0.0/24"]
  }
}

resource "aws_security_group_rule" "p03" {
  type              = "ingress"
  security_group_id = aws_security_group.rules.id
  protocol          = "Tcp"
  from_port         = 22
  to_port           = 22
  cidr_blocks       = ["10.0.0.0/24"]
}

resource "aws_security_group" "p03" {
  name   = "p03"
  vpc_id = aws_vpc.main.id

  ingress {
    protocol    = "Tcp"
    from_port   = 22
    to_port     = 22
    cidr_blocks = ["10.0.0.0/24"]
  }
}

resource "aws_security_group_rule" "p04" {
  type              = "ingress"
  security_group_id = aws_security_group.rules.id
  protocol          = "ALL"
  from_port         = 22
  to_port           = 22
  cidr_blocks       = ["10.0.0.0/24"]
}

resource "aws_security_group" "p04" {
  name   = "p04"
  vpc_id = aws_vpc.main.id

  ingress {
    protocol    = "ALL"
    from_port   = 22
    to_port     = 22
    cidr_blocks = ["10.0.0.0/24"]
  }
}

resource "aws_security_group_rule" "p05" {
  type              = "ingress"
  security_group_id = aws_security_group.rules.id
  protocol          = "All"
  from_port         = 22
  to_port           = 22
  cidr_blocks       = ["10.0.0.0/24"]
}

resource "aws_security_group" "p05" {
  name   = "p05"
  vpc_id = aws_vpc.main.id

  ingress {
    protocol    = "All"
    from_port   = 22
    to_port     = 22
    cidr_blocks = ["10.0.0.0/24"]
  }
}

resource "aws_security_group_rule" "p06" {
  type              = "ingress"
  security_group_id = aws_security_group.rules.id
  protocol          = "all"
  from_port         = 22
  to_port           = 22
  cidr_blocks       = ["10.0.0.0/24"]
}

resource "aws_security_group" "p06" {
  name   = "p06"
  vpc_id = aws_vpc.main.id

  ingress {
    protocol    = "all"
    from_port   = 22
    to_port     = 22
    cidr_blocks = ["10.0.0.0/24"]
  }
}

resource "aws_security_group_rule" "p07" {
  type              = "ingress"
  security_group_id = aws_security_group.rules.id
  protocol          = "-1"
  from_port         = 22
  to_port           = 22
  cidr_blocks       = ["10.0.0.0/24"]
}

resource "aws_security_group" "p07" {
  name   = "p07"
  vpc_id = aws_vpc.main.id

  ingress {
    protocol    = "-1"
    from_port   = 22
    to_port     = 22
    cidr_blocks = ["10.0.0.0/24"]
  }
}

resource "aws_security_group_rule" "p08" {
  type              = "ingress"
  security_group_id = aws_security_group.rules.id
  protocol          = "6"
  from_port         = 22
  to_port           = 22
  cidr_blocks       = ["10.0.0.0/24"]
}

resource "aws_security_group" "p08" {
  name   = "p08"
  vpc_id = aws_vpc.main.id

  ingress {
    protocol    = "6"
    from_port   = 22
    to_port     = 22
    cidr_blocks = ["10.0.0.0/24"]
  }
}

resource "aws_security_group_rule" "p09" {
  type              = "ingress"
  security_group_id = aws_security_group.rules.id
  protocol          = "ICMP"
  from_port         = 22
  to_port           = 22
  cidr_blocks       = ["10.0.0.0/24"]
}

resource "aws_security_group" "p09" {
  name   = "p09"
  vpc_id = aws_vpc.main.id

  ingress {
    protocol    = "ICMP"
    from_port   = 22
    to_port     = 22
    cidr_blocks = ["10.0.0.0/24"]
  }
}

resource "aws_security_group_rule" "p10" {
  type              = "ingress"
  security_group_id = aws_security_group.rules.id
  protocol          = "UDP"
  from_port         = 22
  to_port           = 22
  cidr_blocks       = ["10.0.0.0/24"]
}

resource "aws_security_group" "p10" {
  name   = "p10"
  vpc_id = aws_vpc.main.id

  ingress {
    protocol    = "UDP"
    from_port   = 22
    to_port     = 22
    cidr_blocks = ["10.0.0.0/24"]
  }
}

resource "aws_security_group_rule" "p11" {
  type              = "ingress"
  security_group_id = aws_security_group.rules.id
  protocol          = "icmpv6"
  from_port         = 22
  to_port           = 22
  cidr_blocks       = ["10.0.0.0/24"]
}

resource "aws_security_group" "p11" {
  name   = "p11"
  vpc_id = aws_vpc.main.id

  ingress {
    protocol    = "icmpv6"
    from_port   = 22
    to_port     = 22
    cidr_blocks = ["10.0.0.0/24"]
  }
}

resource "aws_security_group_rule" "p12" {
  type              = "ingress"
  security_group_id = aws_security_group.rules.id
  protocol          = "ICMPV6"
  from_port         = 22
  to_port           = 22
  cidr_blocks       = ["10.0.0.0/24"]
}

resource "aws_security_group" "p12" {
  name   = "p12"
  vpc_id = aws_vpc.main.id

  ingress {
    protocol    = "ICMPV6"
    from_port   = 22
    to_port     = 22
    cidr_blocks = ["10.0.0.0/24"]
  }
}

resource "aws_security_group_rule" "p13" {
  type              = "ingress"
  security_group_id = aws_security_group.rules.id
  protocol          = "58"
  from_port         = 22
  to_port           = 22
  cidr_blocks       = ["10.0.0.0/24"]
}

resource "aws_security_group" "p13" {
  name   = "p13"
  vpc_id = aws_vpc.main.id

  ingress {
    protocol    = "58"
    from_port   = 22
    to_port     = 22
    cidr_blocks = ["10.0.0.0/24"]
  }
}

resource "aws_security_group_rule" "p14" {
  type              = "ingress"
  security_group_id = aws_security_group.rules.id
  protocol          = "17"
  from_port         = 22
  to_port           = 22
  cidr_blocks       = ["10.0.0.0/24"]
}

resource "aws_security_group" "p14" {
  name   = "p14"
  vpc_id = aws_vpc.main.id

  ingress {
    protocol    = "17"
    from_port   = 22
    to_port     = 22
    cidr_blocks = ["10.0.0.0/24"]
  }
}
