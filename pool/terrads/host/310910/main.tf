resource "aws_security_group" "allow_80" {
  name        = "allow_80"
  description = "Allow 80 inbound traffic"
  vpc_id      = "${var.VPC}"

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "TCP"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]

    #prefix_list_ids = ["pl-12c4e678"]
  }
}

resource "aws_security_group" "allow_22" {
  name        = "allow_22"
  description = "Allow 22 inbound traffic"
  vpc_id      = "${var.VPC}"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "TCP"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "allow_4567" {
  name        = "allow_4567"
  description = "Allow 4567 inbound traffic"
  vpc_id      = "${var.VPC}"

  ingress {
    from_port   = 4567
    to_port     = 4567
    protocol    = "TCP"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

#####################################
/*resource "aws_security_group_rule" "first-SG-22-only" {
  type            = "ingress"
  from_port       = 81
  to_port         = 81
  protocol        = "tcp"
  cidr_blocks     = ["0.0.0.0/0"]
  #prefix_list_ids = ["pl-12c4e678"]

  security_group_id = "sg-0016680efb8941892"
}*/

