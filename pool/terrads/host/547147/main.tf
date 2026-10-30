resource "aws_security_group" "k3s" {
  name        = "Termoid-K3s-tf-cluster"
  description = "Allow all traffic"
  vpc_id      = var.vpc_id   

  // Incoming Traffic
  ingress {
    description = "ALL"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  // outgoining traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = {
    Name = var.tag
    "kubernetes.io/cluster/mycluster" = "owned"
  }
}
