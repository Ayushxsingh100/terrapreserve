# This is where you put your outputs declaration

output "vpc_id" {
  value = aws_vpc.vpc.id
}

output "public_subnet1" {
  value = aws_subnet.public-sub1.id
}

output "public_subnet2" {
  value = aws_subnet.public-sub2.id
}

output "private_subnet1" {
  value = aws_subnet.private-sub1.id
}

output "private_subnet2" {
  value = aws_subnet.private-sub2.id
}
