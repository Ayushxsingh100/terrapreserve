terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "5.81.0"
    }
  }
  backend "s3" {
    bucket = "algatux-opentofu-states"
    key    = "states/eks-infrastructure/${var.tfstate_name}"
    region = "eu-west-1"
  }
}

provider "aws" {
  region = var.region
}

resource "aws_subnet" "test-subnet" {
  vpc_id     = var.target_vpc
  cidr_block = var.subnet_cidr

  tags = {
    Name = var.cluster_name
  }
}