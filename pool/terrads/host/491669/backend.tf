terraform {
  backend "s3" {
    bucket                      = "self-state-storage"
    key                         = "ec2/terraform.tfstate"
    region                      = "ap-south-1"
    skip_credentials_validation = true
  }
}
