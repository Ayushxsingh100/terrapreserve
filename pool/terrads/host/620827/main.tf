# ALB Security Group
resource "aws_security_group" "alb" {
  name        = "${var.project_name}-alb-sg"
  description = "Security group for ALB, allowing public ingress and egress to EKS."
  vpc_id      = var.vpc_id

  # Ingress Rule: Allow HTTP from anywhere (public access)
  ingress {
    description = "Allow HTTP from anywhere"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Egress Rule: Allow all outbound traffic from ALB
  egress {
    description = "Allow all outbound from ALB"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-eks-alb"
  }
}


# EKS Cluster Security Group
resource "aws_security_group" "eks_cluster_sg" {
  name        = "${var.project_name}-eks-cluster-sg"
  description = "Security group for the EKS Cluster control plane endpoint."
  vpc_id      = var.vpc_id

  # Only CIDR-based ingress here (e.g., for self-access/VPC internal)
  # All SG-to-SG ingress will be defined as separate aws_security_group_rule resources below
  ingress {
    description = "Allow all from VPC CIDR"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.vpc_cidr_block]
  }

  # Egress Rule: Allow EKS control plane to talk to nodes and other AWS services
  egress {
    description = "Allow all outbound from EKS Cluster control plane"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-eks-cluster-sg"
  }
}


# EKS Node Security Group
resource "aws_security_group" "eks_node_sg" {
  name        = "${var.project_name}-eks-node-sg"
  description = "Security group for EKS worker nodes, allowing communication from ALB and general outbound traffic."
  vpc_id      = var.vpc_id

  # Ingress Rule: Allow All (All Protocols/Ports) from Self (for node-to-node communication)
  # This specific 'self = true' is fine within the resource block
  ingress {
    description = "Allow all from self (node-to-node)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    self        = true
  }

  # Egress Rule: Allow EKS to outbound traffic
  egress {
    description = "Allow all outbound from EKS nodes"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-eks-node-sg"
  }
}


# EFS Security Group
resource "aws_security_group" "efs" {
  name        = "${var.efs_name}-sg"
  description = "Security group for EFS mount targets, allowing NFS traffic from EKS worker nodes and general outbound traffic."
  vpc_id      = var.vpc_id

  # No SG-to-SG ingress rules here, defined separately below.

  # Egress Rule: Allow EFS to make all outbound connections
  egress {
    description = "Allow all outbound traffic from EFS mount targets"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.efs_name}-sg"
  }
}


# Bastion Host Security Group
resource "aws_security_group" "bastion_sg" {
  name        = "${var.project_name}-bastion-sg"
  description = "Security group for the Bastion Host, allowing SSH and outbound access to EKS."
  vpc_id      = var.vpc_id

  # No SG-to-SG ingress rules here, defined separately below.

  # Only CIDR-based egress here. All SG-to-SG egress will be defined as separate rules below.
  egress {
    description = "Allow outbound to internet (e.g., for updates, kubectl downloads)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-bastion-sg"
  }
}


# EKS Node SG: Ingress from ALB (HTTP)
resource "aws_security_group_rule" "eks_node_sg_ingress_from_alb_http" {
  type                     = "ingress"
  from_port                = 80
  to_port                  = 80
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.alb.id
  security_group_id        = aws_security_group.eks_node_sg.id
  description              = "Allow HTTP from ALB"
}

# EKS Node SG: Ingress from EKS Cluster Control Plane (HTTPS)
resource "aws_security_group_rule" "eks_node_sg_ingress_from_eks_cluster_https" {
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.eks_cluster_sg.id
  security_group_id        = aws_security_group.eks_node_sg.id
  description              = "Allow K8s API from EKS Control Plane (HTTPS)"
}

# EKS Node SG: Ingress from EKS Cluster Control Plane (All Protocols)
resource "aws_security_group_rule" "eks_node_sg_ingress_from_eks_cluster_all" {
  type                     = "ingress"
  from_port                = 0
  to_port                  = 0
  protocol                 = "-1"
  source_security_group_id = aws_security_group.eks_cluster_sg.id
  security_group_id        = aws_security_group.eks_node_sg.id
  description              = "Allow all from EKS Control Plane"
}

# EKS Node SG: Ingress from Bastion Host (All Protocols)
resource "aws_security_group_rule" "eks_node_sg_ingress_from_bastion_all" {
  type                     = "ingress"
  from_port                = 0
  to_port                  = 0
  protocol                 = "-1"
  source_security_group_id = aws_security_group.bastion_sg.id
  security_group_id        = aws_security_group.eks_node_sg.id
  description              = "Allow all from Bastion Host"
}

# EFS SG: Ingress from EKS Worker Nodes (NFS)
resource "aws_security_group_rule" "efs_ingress_from_eks_node_sg_https" {
  type                     = "ingress"
  from_port                = 2049
  to_port                  = 2049
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.eks_node_sg.id
  security_group_id        = aws_security_group.efs.id
  description              = "Allow NFS from EKS worker nodes"
}

# EKS Cluster SG: Ingress from EKS Nodes (HTTPS)
resource "aws_security_group_rule" "eks_cluster_sg_ingress_from_eks_nodes_https" {
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.eks_node_sg.id
  security_group_id        = aws_security_group.eks_cluster_sg.id
  description              = "Allow K8s API from EKS Nodes"
}

# EKS Cluster SG: Ingress from Bastion Host (HTTPS)
resource "aws_security_group_rule" "eks_cluster_sg_ingress_from_bastion_https" {
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.bastion_sg.id
  security_group_id        = aws_security_group.eks_cluster_sg.id
  description              = "Allow K8s API from Bastion Host"
}

# Bastion SG: Egress to EKS Cluster API (HTTPS)
resource "aws_security_group_rule" "bastion_sg_egress_to_eks_cluster_api" {
  type                        = "egress"
  from_port                   = 443
  to_port                     = 443
  protocol                    = "tcp"
  source_security_group_id    = aws_security_group.bastion_sg.id
  security_group_id           = aws_security_group.eks_cluster_sg.id
  description                 = "Allow outbound to EKS Cluster API (HTTPS)"
}

# Bastion SG: Egress to EKS Node Group (All traffic)
resource "aws_security_group_rule" "bastion_sg_egress_to_eks_node_group" {
  type                        = "egress"
  from_port                   = 0
  to_port                     = 0
  protocol                    = "-1"
  source_security_group_id    = aws_security_group.bastion_sg.id
  security_group_id           = aws_security_group.eks_node_sg.id
  description                 = "Allow outbound to EKS Node Group (all traffic)"
}

# Bastion SG: Egress to EFS (NFS)
resource "aws_security_group_rule" "bastion_sg_egress_to_efs" {
  type                        = "egress"
  from_port                   = 2049
  to_port                     = 2049
  protocol                    = "tcp"
  source_security_group_id    = aws_security_group.bastion_sg.id
  security_group_id           = aws_security_group.efs.id
  description                 = "Allow outbound to EFS (NFS) from Bastion"
}