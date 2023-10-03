resource "random_string" "this" {
  length           = 16
  special          = true
  override_special = "/@£$"
}

output "random_string" {
	value = random_string.this.result
}