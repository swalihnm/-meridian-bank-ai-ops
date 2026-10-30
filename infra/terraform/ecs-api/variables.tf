variable "name" {
  type    = string
  default = "meridian"
}

variable "region" {
  type    = string
  default = "me-central-1"
}

variable "image" {
  type        = string
  description = "Container image URI, for example an ECR image with a pinned tag."
}

variable "cpu" {
  type    = number
  default = 512
}

variable "memory" {
  type    = number
  default = 1024
}

variable "desired_count" {
  type    = number
  default = 2
}

variable "execution_role_arn" {
  type        = string
  description = "ECS task execution role (needs permission to read the secret)."
}

variable "admin_token_secret_arn" {
  type        = string
  description = "Secrets Manager ARN holding the admin token."
  sensitive   = true
}

variable "subnet_ids" {
  type = list(string)
}

variable "security_group_ids" {
  type = list(string)
}
