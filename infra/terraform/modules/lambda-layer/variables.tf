# infra/terraform/modules/lambda-layer/variables.tf
variable "layer_name" {
  description = "Name of the Lambda layer"
  type        = string
}

variable "description" {
  description = "Description of the layer"
  type        = string
  default     = "Python dependencies layer"
}

variable "compatible_runtimes" {
  description = "List of compatible Lambda runtimes"
  type        = list(string)
  default     = ["python3.12"]
}

variable "s3_bucket" {
  description = "S3 bucket containing the layer zip"
  type        = string
}

variable "s3_key" {
  description = "S3 key for the layer zip"
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
