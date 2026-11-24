resource "aws_security_group" "ec2_sg" {
  vpc_id = var.vpc_id

  ingress {
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [var.load_balancer_security_group_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = var.sg_name
  }
}

# resource "aws_security_group" "ec2_sg" {
#   name        = var.sg_name
#   description = "allow ssh,HTTP,HTTPS traffic through NAT"
#   vpc_id      = var.vpc_id
#   tags = {
#     Name = var.sg_name
#   }
# }

# allow load balancer route 
# resource "aws_security_group_rule" "allow_ssh_lb" {
#   type        = "ingress"
#   description = "SSH ingress"
#   from_port   = 22
#   to_port     = 22
#   protocol    = "tcp"
#   # cidr_blocks       = ["0.0.0.0/0"]
#   source_security_group_id = var.load_balancer_security_group_id
#   security_group_id        = aws_security_group.ec2_sg.id
# }

# resource "aws_security_group_rule" "allow_http_lb" {
#   type        = "ingress"
#   description = "HTTP ingress"
#   from_port   = 80
#   to_port     = 80
#   protocol    = "tcp"
#   # cidr_blocks       = ["0.0.0.0/0"]
#   source_security_group_id = var.load_balancer_security_group_id
#   security_group_id        = aws_security_group.ec2_sg.id
# }

#allow route for NAT gateway 
# resource "aws_security_group_rule" "allow_ssh" {
#   type              = "ingress"
#   description       = ""
#   from_port         = 22
#   to_port           = 22
#   protocol          = "tcp"
#   cidr_blocks       = [for ip in var.nat_gateway_eip : "${ip}/32"]
#   security_group_id = aws_security_group.server_sg.id
# }

# resource "aws_security_group_rule" "allow_http" {
#   type              = "ingress"
#   description       = "HTTP ingress"
#   from_port         = 80
#   to_port           = 80
#   protocol          = "tcp"
#   cidr_blocks       = [for ip in var.nat_gateway_eip : "${ip}/32"]
#   security_group_id = aws_security_group.server_sg.id
# }

# resource "aws_security_group_rule" "allow_https" {
#   type              = "ingress"
#   description       = "HTTPS ingress"
#   from_port         = 443
#   to_port           = 443
#   protocol          = "tcp"
#   cidr_blocks       = [for ip in var.nat_gateway_eip : "${ip}/32"]
#   security_group_id = aws_security_group.server_sg.id
# }

# resource "aws_security_group_rule" "allow_all_outbound" {
#   type              = "egress"
#   description       = "Allow all outbound traffic"
#   from_port         = 0
#   to_port           = 0
#   protocol          = "-1"
#   cidr_blocks       = ["0.0.0.0/0"]
#   security_group_id = aws_security_group.ec2_sg.id
# }
