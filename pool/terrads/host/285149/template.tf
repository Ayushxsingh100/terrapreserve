variable "subnet_size" {
  description = "Size of subnet"
  default = 1
}
variable "availability_zones" {
  description = "Usable availability zones as comma separated list (note: separate each element by comma WITH SPACE like \"us-east-1a, us-east-1b\")"
}

resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
}

resource "aws_subnet" "main" {
  count = "${var.subnet_size}"
  vpc_id = "${aws_vpc.main.id}"
  availability_zone = "${element(split(", ", var.availability_zones),count.index % length(split(", ", var.availability_zones)))}"
  cidr_block = "10.0.${count.index + 1}.0/24"
}

resource "aws_internet_gateway" "main" {
  vpc_id = "${aws_vpc.main.id}"
}

resource "aws_route_table" "main" {
  vpc_id = "${aws_vpc.main.id}"
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = "${aws_internet_gateway.main.id}"
  }
}

resource "aws_route_table_association" "main" {
  count = "${var.subnet_size}"
  subnet_id = "${element(aws_subnet.main.*.id,count.index)}"
  route_table_id = "${aws_route_table.main.id}"
}

resource "aws_security_group" "shared_security_group" {
  name = "SharedSecurityGroup"
  description = "Shared security group over all instances in platform/optional pattern"
  vpc_id = "${aws_vpc.main.id}"
  ingress {
    from_port = 22
    to_port = 22
    protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port = 8501
    to_port = 8501
    protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port = 8300
    to_port = 8302
    protocol = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }
  ingress {
    from_port = 8500
    to_port = 8500
    protocol = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }
  egress {
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

output "vpc_id" {
  value = "${aws_vpc.main.id}"
}

output "subnet_ids" {
  value = "${join(", ", aws_subnet.main.*.id)}"
}

output "shared_security_group" {
  value = "${aws_security_group.shared_security_group.id}"
}
