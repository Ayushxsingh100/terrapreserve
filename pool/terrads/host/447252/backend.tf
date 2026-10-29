terraform {
  backend "s3" {
    bucket  = "infra-vpc-backend"
    encrypt = true
    region  = "us-east-1"
    key     = "terraform_backend/terraform.tfstate"
  }
}
