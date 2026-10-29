resource "aws_security_group" "bastion" {
    name = "${var.project}-${var.environment}-bastion-sg"
    description = "Bastion host security group"
    vpc_id = var.vpc_id

    ingress {
        description = "SSH from trusted CIDRs only"
        from_port = 22
        to_port = 22
        protocol = "tcp"
        cidr_blocks = var.allowed_ssh_cidrs
    }

    egress {
        description = "allow all outbound traffic from bastion"
        from_port = 0
        to_port = 0
        protocol = "-1" #-1 means all protocols
        cidr_blocks = ["0.0.0.0/0"]
    }

    tags = merge (
        local.common_tags,        {
            Name = "${var.project}-${var.environment}-bastion-sg"
        }   
    )
}

