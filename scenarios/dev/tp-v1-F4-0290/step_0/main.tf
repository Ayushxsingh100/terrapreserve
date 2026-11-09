# The security group of the Web Tier's ALB 
resource "aws_security_group" "trident_web_alb_sg" {
  name                   = "${var.name_prefix}-${var.sg_names["web_alb"]}"
  description            = "Allows HTTP/S public entry"
  revoke_rules_on_delete = true
  vpc_id                 = var.vpc_id

  dynamic "ingress" {                  # Dynamic blocks is useful for multiple ports, its good practice to use them as they are powerful, though overuse can make the code complicated 
    for_each = var.sg_ports["web_alb"] # "web_alb" is the key in the sg_ports map. It defines which ports to allow for this SG.
    iterator = port
    content {
      from_port   = port.value
      to_port     = port.value
      cidr_blocks = ["0.0.0.0/0"]
      protocol    = "tcp"
    }
  }

  # Allow all outbound traffic 
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.name_prefix}-${var.sg_names["web_alb"]}"
  }
}

# The security group of the Web Tier's EC2 instances 
resource "aws_security_group" "trident_web_sg" {
  name                   = "${var.name_prefix}-${var.sg_names["web"]}"
  description            = "Protect Web EC2 from public access"
  revoke_rules_on_delete = true
  vpc_id                 = var.vpc_id

  dynamic "ingress" {
    for_each = var.sg_ports["http"]
    iterator = port
    content {
      from_port       = port.value
      to_port         = port.value
      protocol        = "tcp"
      security_groups = [aws_security_group.trident_web_alb_sg.id]
    }
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.name_prefix}-${var.sg_names["web"]}"
  }
}

# The security group of the App's ALB 
resource "aws_security_group" "trident_app_alb_sg" {
  name                   = "${var.name_prefix}-${var.sg_names["app_alb"]}"
  description            = "Allows traffic from Web Tier"
  revoke_rules_on_delete = true
  vpc_id                 = var.vpc_id

  dynamic "ingress" {
    for_each = var.sg_ports["http"]
    iterator = port
    content {
      from_port       = port.value
      to_port         = port.value
      protocol        = "tcp"
      security_groups = [aws_security_group.trident_web_sg.id]
    }
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.name_prefix}-${var.sg_names["app_alb"]}"
  }
}

# The App's security group for 
resource "aws_security_group" "trident_app_sg" {
  name                   = "${var.name_prefix}-${var.sg_names["app"]}"
  description            = "Protects App EC2 from public"
  revoke_rules_on_delete = true
  vpc_id                 = var.vpc_id

  dynamic "ingress" {
    for_each = var.sg_ports["http"]
    iterator = port
    content {
      from_port       = port.value
      to_port         = port.value
      protocol        = "tcp"
      security_groups = [aws_security_group.trident_app_alb_sg.id]
    }
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.name_prefix}-${var.sg_names["app"]}"
  }
}

# The database security group, allows inbound traffic from App EC2 
resource "aws_security_group" "trident_data_sg" {
  name                   = "${var.name_prefix}-${var.sg_names["data"]}"
  description            = "Allows communication with App EC2"
  revoke_rules_on_delete = true
  vpc_id                 = var.vpc_id

  dynamic "ingress" {
    for_each = var.sg_ports["database"]
    iterator = port
    content {
      from_port       = port.value
      to_port         = port.value
      protocol        = "tcp"
      security_groups = [aws_security_group.trident_app_sg.id]
    }
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.name_prefix}-${var.sg_names["data"]}"
  }
}
