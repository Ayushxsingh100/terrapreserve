terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      # fixed version needed due to Localstack issue
      # https://github.com/localstack/localstack/issues/13426
      version = "6.22.0"
    }
  }
}