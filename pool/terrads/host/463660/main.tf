resource "aws_security_group" "main" {
  count = length(var.security-group-name)
  name = var.security-group-name[count.index]
  description = var.security-group-description[count.index]
  vpc_id = var.vpc-id
  dynamic "ingress" {
    for_each = var.ingress-access
    content {
        from_port = ingress.value["from-port"]
        to_port = ingress.value["to-port"]
        protocol = ingress.value["protocol"]
        cidr_blocks = ingress.value["cidr"]
        description = ingress.value["description"]
    }
  }
}