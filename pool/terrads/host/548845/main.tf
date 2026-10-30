# Define resource block for provisioning a security group allowing SSH, HTTP, and HTTPS traffic

resource "aws_security_group" "allow_ssh_http_https" {
  name        = var.sg_name        # Specify the name of the security group
  description = var.sg_description # Specify the description of the security group
  tags        = var.sg_tag         # Specify tags for the security group
  
  # Ingress rules for SSH, HTTP, and HTTPS traffic
  ingress {
    from_port        = 22           # SSH port
    to_port          = 22           # SSH port
    protocol         = "tcp"        # TCP protocol
    cidr_blocks      = ["0.0.0.0/0"]  # Allow traffic from all IPv4 addresses
    ipv6_cidr_blocks = ["::/0"]      # Allow traffic from all IPv6 addresses
  }

  ingress {
    from_port        = 80           # HTTP port
    to_port          = 80           # HTTP port
    protocol         = "tcp"        # TCP protocol
    cidr_blocks      = ["0.0.0.0/0"]  # Allow traffic from all IPv4 addresses
    ipv6_cidr_blocks = ["::/0"]      # Allow traffic from all IPv6 addresses
  }

  ingress {
    from_port        = 443          # HTTPS port
    to_port          = 443          # HTTPS port
    protocol         = "tcp"        # TCP protocol
    cidr_blocks      = ["0.0.0.0/0"]  # Allow traffic from all IPv4 addresses
    ipv6_cidr_blocks = ["::/0"]      # Allow traffic from all IPv6 addresses
  }

  # Egress rule allowing all traffic
  egress {
    from_port        = 0            # All ports
    to_port          = 0            # All ports
    protocol         = "-1"         # All protocols
    cidr_blocks      = ["0.0.0.0/0"]  # Allow traffic to all IPv4 addresses
    ipv6_cidr_blocks = ["::/0"]      # Allow traffic to all IPv6 addresses
  }
}
