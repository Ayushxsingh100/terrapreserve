#GP cdw instances configuration 
variable "instances" {
  type = map(object({
	ami       	= string
	instance_type = string
    name = string 
    volumeSize = number
  }))
  default = {
	gp-coordinator = {name = "cdw", ami = "ami-05150ea4d8a533099", instance_type = "r5.xlarge" , volumeSize = 500 }
   #replace cdw ec2 default properties with your ec2 properties , add another row of "gp-coordinator" for 2 cdw instances
  }
}

#GP sdw instances configuration 
variable "instances-sdw" {
 type    = list(object({
  ami = string   
	instance_type = string
  name = string 
  volumeSize = number
 }))
 default = [{
   ami           = "ami-05150ea4d8a533099"  #replace with your ami id default is rocky linux 9 ami id
   instance_type = "r5.4xlarge"   #replace with your ec2 size
   volumeSize = 500
   name = "sdw"
 }
 ]
}

#GP EC2(vm) aws ssh key name
variable "key_name" {
  type        = string
  description = "Name tag for the instance"
  default = "abhi-gp" #replace with your key name
}

#GP sdw ec2 nodes count
variable "count_sdw" {
 type    = number
 default = 3
}