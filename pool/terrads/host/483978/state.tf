terraform {
  backend "s3" {
    bucket  = "terraform-statefile-star-wars-374626184495"
    key     = "tfstate/vpc/vpc-devstaff-dev.tfstate"
    region  = "eu-west-1"
    profile = "star-wars-profile"
    encrypt = true
  }
}