 # EKS control plane is AWS-managed.
  # No custom ingress rules are required here.
  # Worker nodes and kubectl access are handled by AWS-managed SGs,
  # IAM authentication, and Kubernetes RBAC.
  # There is no ingress needed from outside to the control plane SG because it is managed by AWS.
  # Egress rules are needed to allow the control plane to communicate with worker nodes.
resource "aws_security_group" "eks_control_plane" {
    name = "${var.project}-${var.environment}-eks-controlplane-sg"
    description = "EKS Control Plane Security Group"
    vpc_id = var.vpc_id


    #Only egress rules needed to communicate with worker nodes. Ingress only managed by worker nodes
    egress {
        description = "Allow all outbound traffic"
        from_port = 0
        to_port = 0
        protocol = "-1"
        cidr_blocks = ["0.0.0.0/0"]
    }

    tags = merge(
        local.common_tags,
        {
            Name = "${var.project}-${var.environment}-eks-controlplane-sg"
        }
    )
}

/* #This is only for self managed nodes. Usually aws managed node groups automatically have these rules 
resource "aws_security_group" "eks_nodes" {
    name = "${var.project}-${var.environment}-eks-nodes-sg"
    description = "EKS worker nodes security group"
    vpc_id = var.vpc_id

    ingress {
        description = "allow all traffic from node-to-node communication"
        from_port = 0
        to_port = 0
        protocol = "-1"
        self = true
    }
    #Why this rule? -> Because control plane needs to communicate with worker nodes on these ports
    #what are these port? -> These are ephemeral ports used for communication
    #1025-65535 are the range of ephermeral ports
    ingress {
        description = "control plane to nodes"
        from_port = 1025
        to_port = 65535
        protocol = "tcp"
        security_groups = [aws_security_group.eks_control_plane.id]
    }

    #VPC internal traffic
    ingress {
        description = "vpc internal traffic"
        from_port = 0
        to_port = 0
        protocol = "-1"
        cidr_blocks = [var.vpc_cidr]
    }

    egress{
        description = "allow all outbound traffic"
        from_port = 0
        to_port = 0
        protocol = "-1"
        cidr_blocks = ["0.0.0.0/0"]
    }

    tags = merge (
        local.common_tags,
        {
            Name = "${var.project}-${var.environment}-eks-nodes-sg"
        }   
    )
}

 */