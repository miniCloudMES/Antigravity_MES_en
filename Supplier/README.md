# Supplier App (Supplier Management Module)

## Description
The Supplier module manages basic supplier records for the factory. It provides supplier categorization, contact details management, and connects with the `Material` module as the default source for raw material purchasing.

## Models
* **SupplierCategory**: Categorizes suppliers into types, such as "Electronic Components", "Raw Material Wholesalers", "Logistics Providers", etc.
* **Supplier**: Stores supplier code (unique), company name, tax ID, contact person, phone, email, address, and remarks.

## Key Features & Logic
* **Supply Chain Association**:
  * Each `Material` can be assigned a default `Supplier`. When stock falls below the safety threshold, the system can quickly filter the corresponding default vendor for procurement.

## Change Notice
* The module provides standard CRUD interfaces with no major business logic changes in this release.
