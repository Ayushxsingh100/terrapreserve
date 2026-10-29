# Terraform provider configuration
provider "aws" {
  region = "us-east-1"  # Change to your desired region
}

# Resource: Security Group allowing SSH access
resource "aws_security_group" "ssh_sg" {
  name        = "ssh-security-group"
  description = "Allow SSH access"

  # Ingress rule: Allow SSH access on port 22 from any IP (0.0.0.0/0)
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Egress rule: Allow all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Resource: EC2 instance with a custom AMI (using Ubuntu's public AMI)
resource "aws_instance" "ubuntu_instance" {
  ami             = "ami-084568db4383264d4"  # Example Ubuntu AMI ID (change for your region)
  instance_type   = "t2.micro"  # Choose the desired instance type
  key_name        = "my-ssh-key"  # Replace with your SSH key name
  security_groups = [aws_security_group.ssh_sg.name]
  
  # Optional: Tag the instance for better identification
  tags = {
    Name = "Ubuntu-Instance"
  }
}
