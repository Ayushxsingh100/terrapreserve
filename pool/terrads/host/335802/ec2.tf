# SSH keypair

/*
resource "aws_key_pair" "demoVPC" {
    key_name = "demoVPC-key"
    public_key = 
}
*/

# Provision EC2 Instance and deploy webserver in public subnet

resource "aws_instance" "WebServer" {
    ami = var.ami_id
    availability_zone = "us-east-2a"
    instance_type = var.instance_type
    subnet_id = aws_subnet.publicSN.id
    # vpc_security_group_ids = aws_security_group.webSG.id
    associate_public_ip_address = true
    source_dest_check = false
    # user_data = file("$path.module}/hello.txt")

    tags = {
        Name = "Web Server"
    }
}

/*
resource "aws_instance" "DatabaseServer" {
    ami = var.ami_id
    instance_type = var.instance_type
    subnet_id = aws_subnet.privateSN.id
    # vpc_security_group_ids = aws_security_group.dbSG.id
    associate_public_ip_address = true
    source_dest_check = false
    # user_data = file("$path.module}/hello.txt")

    tags = {
        Name = "Database Server"
    }
}
*/
