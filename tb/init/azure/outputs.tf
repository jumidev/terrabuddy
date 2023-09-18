output "account_id" {
  description = "Id of the storage account created."
  value       = azurerm_storage_account.storage.id
}

output "account_name" {
  description = "Name of the storage account created."
  value       = azurerm_storage_account.storage.name
}

output "container_id" {
  description = "Name of the storage account created."
  value       = azurerm_storage_container.terraform.id
}

output "container_name" {
  description = "Name of the storage account created."
  value       = azurerm_storage_container.terraform.name
}