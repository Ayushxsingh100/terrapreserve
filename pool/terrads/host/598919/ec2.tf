resource "aws_instance" "web" {
ami = "ami-0c55b159cbfafe1f0"
instance_type = "t2.micro"
subnet_id = aws_subnet.public.id
security_groups = [aws_security_group.web_sg.name]
key_name = "your-key-pair"
tags = {
Name = "web-instance"
}
}
resource "aws_instance" "app" {
ami = "ami-0c55b159cbfafe1f0"
instance_type = "t2.micro"
subnet_id = aws_subnet.app.id
security_groups = [aws_security_group.app_sg.name]
key_name = "your-key-pair"
tags = {
Name = "app-instance"
}
}
resource "aws_instance" "db" {
ami = "ami-0c55b159cbfafe1f0"
instance_type = "t2.micro"
subnet_id = aws_subnet.db.id
security_groups = [aws_security_group.db_sg.name]
key_name = "your-key-pair"
tags = {
Name = "db-instance"
}
}
resource "aws_instance" "bastion" {
ami = "ami-0c55b159cbfafe1f0"
instance_type = "t2.micro"
subnet_id = aws_subnet.public.id
key_name = "your-key-pair"
tags = {
Name = "bastion-host"
}
}