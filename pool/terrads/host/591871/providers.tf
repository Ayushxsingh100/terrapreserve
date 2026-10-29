/*
The reason we didnt pass a provider/region for this is that we are using the provider_main module for this
however each subdirectory must sill reference that it is using terraform
*/

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0.0"
    }
  }
}
