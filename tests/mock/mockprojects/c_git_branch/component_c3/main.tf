variable "a1" {
  type = map(any)
}

output "a1" {
  value = lookup(var.a1, "block1").foo
}

