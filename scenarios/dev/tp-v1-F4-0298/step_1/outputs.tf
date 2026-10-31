output "public_subnet_id" {
  value = "${aws_subnet.public.id}"
}

output "private_subnet_id" {
  value = "${aws_subnet.private.id}"
}

output "manage_subnet_id" {
  value = "${aws_subnet.manage.id}"
}

output public_route_table_id {
  value = "${aws_route_table.public_internet.id}"
}

output private_route_table_id {
  value = "${aws_route_table.private.id}"
}

output manage_route_table_id {
  value = "${aws_route_table.manage.id}"
}
