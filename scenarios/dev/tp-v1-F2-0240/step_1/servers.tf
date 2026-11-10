
resource "aws_instance" "secondserver" {
  ami           = "${var.tp_ds_aws_ami_ubuntu.id}"
  instance_type = "t2.micro"

  tags = {
    Name = "identifiertag"
  }
}

