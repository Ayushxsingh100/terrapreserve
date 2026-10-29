variable "deployment_branch" {
  type = string
}

variable "app_name" {
  type = string
}

variable "subdomain_game_stacks" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "vpc_cidr_block" {
  type = string
}

variable "public_subnet_id_a" {
  type = string
}

variable "public_subnet_id_b" {
  type = string
}

variable "proxy_server_port" {
  type = string
}

variable "game_server_port" {
  type = number
}

variable "game_server_name_container" {
  type = string
}

# variable "hosted_zone_name" {
#   type = string
# }

# variable "hosted_zone_id" {
#   type = string
# }




## ALB ACM

# resource "aws_acm_certificate" "alb_certificate" {
#   domain_name       = "${var.subdomain_game_stacks}.${var.hosted_zone_name}"
#   validation_method = "DNS"
# }

# resource "aws_route53_record" "dns_record" {
#   for_each = {
#     for dvo in aws_acm_certificate.alb_certificate.domain_validation_options : dvo.domain_name => {
#       name   = dvo.resource_record_name
#       record = dvo.resource_record_value
#       type   = dvo.resource_record_type
#     }
#   }

#   allow_overwrite = true
#   name            = each.value.name
#   records         = [each.value.record]
#   ttl             = 60
#   type            = each.value.type
#   zone_id         = var.hosted_zone_id

# }

# resource "aws_acm_certificate_validation" "alb_certificate_validation" {
#   certificate_arn         = aws_acm_certificate.alb_certificate.arn
#   validation_record_fqdns = [for record in aws_route53_record.dns_record : record.fqdn]
# }


## ALB

resource "aws_security_group" "sg_alb" {
  name        = "sg_alb_${var.game_server_name_container}_${var.deployment_branch}"
  description = "ALB security group"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = var.proxy_server_port
    to_port     = var.proxy_server_port
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = var.proxy_server_port
    to_port     = var.proxy_server_port
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = var.game_server_port
    to_port     = var.game_server_port
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = var.game_server_port
    to_port     = var.game_server_port
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

output "security_group_alb_id" {
  value = aws_security_group.sg_alb.id
}



# resource "aws_lb" "alb_game_server" {
#   name               = "${var.app_name}-alb-${var.game_server_name_container}-${var.deployment_branch}"
#   internal           = false
#   load_balancer_type = "application"
#   security_groups    = [aws_security_group.sg_alb.id]
#   subnets            = [var.public_subnet_id_a, var.public_subnet_id_b]

# }

# ## Alias
# resource "aws_route53_record" "alb_alias" {
#   zone_id = var.hosted_zone_id
#   name    = "${var.subdomain_game_stacks}.${var.hosted_zone_name}"
#   type    = "A"

#   alias {
#     name                   = aws_lb.alb_game_server.dns_name
#     zone_id                = aws_lb.alb_game_server.zone_id
#     evaluate_target_health = true
#   }
# }


# ## Target groups

# resource "aws_alb_target_group" "gameserver_target_group_ws" {
#   name        = "target-${var.game_server_name_container}-ws-${var.deployment_branch}"
#   port        = var.proxy_server_port
#   protocol    = "HTTPS"
#   vpc_id      = var.vpc_id
#   target_type = "ip"
#   target_health_state {
#     enable_unhealthy_connection_termination = false
#   }

#   health_check {
#     path                = "/"
#     port                = "traffic-port"
#     protocol            = "HTTPS"
#     healthy_threshold   = 3
#     unhealthy_threshold = 3
#     matcher             = "404"
#   }
# }

# resource "aws_alb_target_group" "gameserver_target_group_https" {
#   name        = "target-${var.game_server_name_container}-https-${var.deployment_branch}"
#   port        = 443
#   protocol    = "HTTPS"
#   vpc_id      = var.vpc_id
#   target_type = "ip"

#   target_health_state {
#     enable_unhealthy_connection_termination = false
#   }

#   health_check {
#     path                = "/"
#     port                = "traffic-port"
#     protocol            = "HTTPS"
#     healthy_threshold   = 3
#     unhealthy_threshold = 3
#     matcher             = "404"
#   }
# }

# output "target_group_game_server_ws_arn" {
#   value = aws_alb_target_group.gameserver_target_group_ws.arn
# }

# output "target_group_game_server_https_arn" {
#   value = aws_alb_target_group.gameserver_target_group_https.arn
# }

# ## 443 listener
# resource "aws_alb_listener" "game_server_alb_listener_443" {
#   depends_on        = [aws_acm_certificate_validation.alb_certificate_validation]
#   load_balancer_arn = aws_lb.alb_game_server.arn
#   port              = 443
#   protocol          = "HTTPS"
#   ssl_policy        = "ELBSecurityPolicy-2016-08"
#   certificate_arn   = aws_acm_certificate.alb_certificate.arn


#   default_action {
#     target_group_arn = aws_alb_target_group.gameserver_target_group_https.arn
#     type             = "forward"
#   }

# }

# ## 27961 listener
# resource "aws_alb_listener" "game_server_alb_listener_27961" {
#   depends_on        = [aws_acm_certificate_validation.alb_certificate_validation]
#   load_balancer_arn = aws_lb.alb_game_server.arn
#   port              = var.proxy_server_port
#   protocol          = "HTTPS"
#   ssl_policy        = "ELBSecurityPolicy-2016-08"
#   certificate_arn   = aws_acm_certificate.alb_certificate.arn


#   default_action {
#     target_group_arn = aws_alb_target_group.gameserver_target_group_ws.arn
#     type             = "forward"
#   }

# }

# ## Outputs


# output "load_balancer_https_url" {
#   value = aws_route53_record.alb_alias.name
# }


