locals {
  snake_case_name = join("_", regexall("[[:alnum:]]+", lower(var.name)))
}
