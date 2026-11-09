


resource "aws_instance" "server" {
  ami = "${var.tp_ds_aws_ami_ubuntu.id}"
  instance_type = "t2.micro"

  tags = {
    Name = "terraform-instance-1"
  }

  subnet_id = "${aws_subnet.subnet2.id}"

}