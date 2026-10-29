output "vpc" {
	value = "${aws_vpc.my-main.id}"
}

output "sn_priv1" {
	value = "${aws_subnet.my-private1.id}"
}