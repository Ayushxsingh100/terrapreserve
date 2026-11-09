locals {
  allowed_instance_types = ["t2.micro", "t3.micro"]
}

data "aws_ami" "ubuntu" {

  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-*-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

}

resource "aws_instance" "compute" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.instance_type
  subnet_id     = aws_subnet.this.id

  root_block_device {
    delete_on_termination = true
    volume_size           = 10
    volume_type           = "gp3"
  }

  lifecycle {
    precondition {
      condition     = contains(local.allowed_instance_types, var.instance_type)
      error_message = "var - Invalid instance type. Only t2.micro and t3.micro are allowed."
    }

    postcondition {
      condition     = contains(local.allowed_instance_types, self.instance_type)
      error_message = "Self - Invalid instance type. Only t2.micro and t3.micro are allowed."
    }
  }
}

check "cost_enter_check" {
  assert {
    condition     = can(aws_instance.compute.tags.CostCenter != "")
    error_message = "Cost check failed. Ensure the instance type is within budget."
  }
}