# Product App (Product Master Module)

## Description
The Product module manages finished goods master data manufactured by the factory. It defines specifications, drawing numbers, and versions, serving as the root entity for Bills of Materials (BOM) and standard process route cards.

## Models
* **ProductCategory**: Categorizes finished products into product lines, such as "Electronic Products", "Accessories", etc.
* **Product**: Stores product ID (unique and used as business key), product name, specification, image, engineering drawing number (`drawing_no`), version (`version`), and active status.

## Key Features & Logic
* **Engineering & Version Management**:
  * Supports recording drawing numbers and finished product versions so BOMs match the correct product version during design changes.
* **Production Module Association**:
  * Each `Product` can have an active `BOM` (Bill of Materials) and multiple `ProcessStep` records composing the process route card for that product.

## Change Notice
* The `product_id` must match the finished good material code in the `Material` module to enable automatic inventory incrementation upon work order completion.
