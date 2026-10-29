terraform {
  required_version = "1.8.1"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "5.45.0"
    }
  }

  backend "s3" {
    bucket = "daniloanobre-remote-state"
    key    = "workspaces/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region  = "us-east-1"
  profile = "tf001"

  default_tags {
    tags = {
      owner      = "Danilo Assis"
      managed-by = "Terraform"
    }
  }
}
