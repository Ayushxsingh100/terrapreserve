# Criar Security Group para Instâncias Privadas
resource "aws_security_group" "private_sg" {
  vpc_id      = var.vpc_id
  name        = local.backend_security_group_name
  description = "Security Group para instancias privadas"

  # Regra de entrada: Permitir tráfego HTTP (porta 80) apenas de instâncias públicas
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.public_subnets_cidr_blocks # Subnets públicas
    description = "Permitir HTTP de subnets publicas"
  }

  # Regra de entrada: Permitir tráfego MySQL (porta 3306) de subnets públicas
  ingress {
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    cidr_blocks = var.public_subnets_cidr_blocks # Subnets públicas
    description = "Permitir trafego MySQL de subnets publicas"
  }

  # Regra de entrada: Permitir tráfego entre as instâncias privadas (mesma subnet)
  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = var.private_subnets_cidr_blocks # Subnets privadas
    description = "Permitir trafego entre instancias privadas"
  }

  # Regra de saída: Permitir todo o tráfego de saída (padrão)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Permitir todo o trafego de saida"
  }

  tags = {
    Name  = local.backend_security_group_name
    owner = var.tag_owner
  }
}