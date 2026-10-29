# Grupo de Seguridad para instancias EC2.
# Define las reglas de firewall para las instancias EC2.
resource "aws_security_group" "ec2" {
  name_prefix = "${var.project_name}-${var.environment}-ec2-"
  vpc_id = var.vpc_id

  # Permite el tráfico desde el ALB a la aplicación Flask en el puerto 5000.
  ingress {
    from_port       = 5000
    to_port         = 5000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
    description     = "Allow traffic from ALB to Flask app"
  }

  # Permite el acceso SSH desde cualquier IP (para administración).
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # Se recomienda restringir a tu IP.
    description = "SSH access for administration"
  }

  # Permite todo el tráfico saliente.
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-ec2-sg"
  }

}

# Grupo de Seguridad para RDS.
# Define las reglas de firewall para la base de datos RDS.
resource "aws_security_group" "rds" {
  name_prefix = "${var.project_name}-${var.environment}-rds-sg"
  vpc_id = var.vpc_id

  # Permite el acceso a MySQL desde las instancias EC2.
  ingress {
    from_port = 3306
    to_port = 3306
    protocol = "tcp"
    security_groups = [aws_security_group.ec2.id]
    description = "Allow MySQL access from EC2"
  }

  # Permite todo el tráfico saliente.
  egress {
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-rds-sg"
  }
}

# Grupo de Seguridad para el Balanceador de Carga.
# Define las reglas de firewall para el Application Load Balancer.
resource "aws_security_group" "alb" {
  name_prefix = "${var.project_name}-${var.environment}-alb-"
  vpc_id = var.vpc_id

  # Permite el tráfico HTTP desde cualquier lugar.
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP access from anywhere"
  }

  # Permite el tráfico HTTPS desde cualquier lugar.
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS access from anywhere"
  }

  # Permite todo el tráfico saliente.
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-alb-sg"
  }
}