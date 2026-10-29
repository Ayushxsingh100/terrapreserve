variable "aws_region" { }
variable "vpcid" { }
variable "prefix" { }
variable "owner" { }
variable "se-region" { }
variable "purpose" { }
variable "ttl" { }
variable "terraform" { }

provider "aws" {
    region = var.aws_region
}

resource "aws_security_group" "jenkins-server-sg" {
    name = "jenkins-server-sg"
    description = "Jenkins server security group"
    vpc_id = var.vpcid

    ingress {
        from_port = 22
        to_port = 22
        protocol = "tcp"
        cidr_blocks = ["0.0.0.0/0"]
    }

    ingress {
       from_port = 8080
       to_port = 8080
       protocol = "tcp"
       cidr_blocks = ["0.0.0.0/0"]
    }

    ingress {
       from_port = 9000
       to_port = 9000
       protocol = "tcp"
       cidr_blocks = ["0.0.0.0/0"]
    }

    egress {
        from_port = 0
        to_port = 0
        protocol = "-1"
        cidr_blocks = ["0.0.0.0/0"]
    }

    tags = {
        Name = "${var.prefix}-jenkins-demo"
        owner = var.owner
        se-region = var.se-region
        purpose = var.purpose
        ttl = var.ttl
        terraform = var.terraform
    }
}

output "id" {
    value = aws_security_group.jenkins-server-sg.id
}
