variable "network" {
  description = "Network variable, with vpc cidr, a list of subnets and nat-gateways, to give controled access to internet"

  type = object(
    {
      cidr = string
      subnets = map(object(
        {
          external = optional(bool)
        }
      ))
    }
  )
}