
# ----------------------------------- Security Groups for the EC2 Instances -------------------------- #

# Security group for Public EC2 Instance

resource "aws_security_group" "Lab1FridayHITTPublicEC2InstanceSGrp" {
    vpc_id = var.vpc_id
    description = "Allow SSH login to Public EC2 instance"

    ingress {
        from_port = 22
        to_port = 22
        protocol = "tcp"
        security_groups = [aws_security_group.Lab1FridayHITTJumpBoxSGrp.id]
    }
    ingress {
        from_port = 80                                    #Allows HTTP connection
        to_port = 80
        protocol = "tcp"
        cidr_blocks = ["0.0.0.0/0"]
    }
    ingress {
        from_port = 443                                  #Allows HTTPS connection
        to_port = 443
        protocol = "tcp"
        cidr_blocks = ["0.0.0.0/0"]
    }
    ingress {
        from_port = 8
        to_port = 0
        protocol = "icmp"
        cidr_blocks = ["10.24.1.0/24"]
   }
   egress {
    description = "All outbound rules outside"
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = [ "0.0.0.0/0" ]
   }
    tags = {
        Name = "Lab2-PublicEC2SGrp"
    }
  
}

# Security Group for the Private EC2 instance in private subnet

resource "aws_security_group" "Lab1FridayHITTPrivateEC2InstanceSGrp" {
    vpc_id = var.vpc_id
    description = "Allow SSH from the Jump Box from public subnet"

    ingress {                                                    #Allow SSH from jump box
        from_port = 22
        to_port = 22
        protocol = "tcp"
        security_groups = [aws_security_group.Lab1FridayHITTJumpBoxSGrp.id]
    }

    ingress {                                                    # Allow ping from jump box
        from_port = 8
        to_port = 0
        protocol = "icmp"
        cidr_blocks = ["10.24.0.0/24"]
    }

    tags = {
      Name = "Lab2-PrivateEC2SGrp"
    }

  
}

# Security group for Jump box in public subnet

resource "aws_security_group" "Lab1FridayHITTJumpBoxSGrp" {
    vpc_id = var.vpc_id
    description = "Allow SSH to the jump host for specific IP range"

    ingress {
        from_port = 22
        to_port = 22
        protocol = "tcp"
        cidr_blocks = [ "0.0.0.0/0" ]                # Good to use VPN range
    }

    ingress {
        from_port = 8
        to_port = 0
        protocol = "icmp"
        cidr_blocks = [ "0.0.0.0/0" ]
    }
    egress {
        from_port = 0
        to_port = 0
        protocol = "-1"
        cidr_blocks = [ "0.0.0.0/0" ]
    }
    tags = {
      Name = "Lab2-JumpBoxEC2SGrp"
    }
  
}
# ------------------------------- EC2 Instances ------------------------------- #

# Public EC2 Instance

resource "aws_instance" "Lab1FridayHITTPublicEC2Instance" {
    instance_type = var.InstanstanceType
    key_name = var.KeyNameEC2
    ami = var.ami_id
    subnet_id = var.public_subnet
    vpc_security_group_ids = [aws_security_group.Lab1FridayHITTPublicEC2InstanceSGrp.id]
    tags = {
      Name = "Lab2-PublicEC2Instance"
    
    }
  
}
# Private EC2 Instance

resource "aws_instance" "Lab1FridayHITTPrivateEC2Instance" {
    instance_type = var.InstanstanceType
    key_name = var.KeyNameEC2
    ami = var.ami_id
    subnet_id = var.private_subet
    vpc_security_group_ids = [aws_security_group.Lab1FridayHITTPrivateEC2InstanceSGrp.id]
    tags = {
      Name = "Lab2-PrivateEC2Instance"
    
    }
  
}

# Jump Host Instance
resource "aws_instance" "Lab1FridayHITTJumpBox" {
  ami             = var.ami_id
  instance_type   = var.InstanstanceType
  key_name        = var.KeyNameEC2
  subnet_id       = var.public_subnet
  vpc_security_group_ids = [aws_security_group.Lab1FridayHITTJumpBoxSGrp.id]

  tags = {
    Name = "Lab2-JumpBox"
  }
}