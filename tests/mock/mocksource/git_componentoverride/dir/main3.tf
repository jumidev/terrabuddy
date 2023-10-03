resource "random_string" "this2" {
  length           = 16
  special          = true
  override_special = "/@£$"
}

output "random_string2" {
	value = random_string.this2.result
}