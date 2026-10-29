

resource "aws_security_group" "sg" {
  name        = "sg"
  description = "Allow TLS inbound traffic"
  vpc_id      = "vpc-123"

  ingress {
    description = "TLS from VPC"
    from_port   = var.port
    to_port     = var.port
    protocol    = "tcp"
    cidr_blocks = var.cidrs
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name                 = "allow_ssh"
    git_commit           = "42d7d387f7aa3eb58745d74f567729f5f5bca493"
    git_file             = "terraform/aws/modules/security_group/main.tf"
    git_last_modified_at = "2023-03-01 20:22:35"
    git_last_modified_by = "40035609+ghouldaemon@users.noreply.github.com"
    git_modifiers        = "40035609+ghouldaemon"
    git_org              = "ghouldaemon"
    git_repo             = "terragoated"
    yor_trace            = "02dd6ff5-f153-4c6d-bc14-24ca7414b0b4"
    yor_name             = "sg"
  }
}
