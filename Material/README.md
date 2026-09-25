# Material App (Materials & Inventory Module)

## Description
The Material module manages factory inventory for raw materials, semi-finished goods, and finished goods. It provides material master data maintenance, safety stock monitoring, and stock transaction tracking (inbound, outbound, and adjustment).

## Models
* **MaterialCategory**: Categorizes materials, such as "Electronic Components", "Metal Enclosures", "Packaging Materials", etc.
* **Material**: Stores material ID (unique), name, unit of measure, current stock quantity (`stock_quantity`), safety stock threshold (`min_stock`), default storage location, and supplier.
* **StockTransaction**: Records detailed inventory movements, including transaction type (`INBOUND`, `OUTBOUND`, `ADJUST`), quantity, balance after transaction (`balance_after`), document reference number (e.g. work order number), and operator.

## Key Features & Logic
* **Low Stock Warning (is_low_stock)**:
  * When `stock_quantity <= min_stock` and safety stock is greater than 0, the material is flagged as low stock and displayed on the home dashboard for procurement alerts.
* **Balance Tracking (balance_after)**:
  * Each manual or automated stock transaction records the stock balance at that moment for auditability and traceability.
* **Production Completion / Kitting Verification Linkage**:
  * In coordination with the Production module, verifies inventory sufficiency and atomically deducts raw material stock upon work order completion.

## Change Notice
* Work order completion automatically verifies if a corresponding `Material` record exists for the finished product ID; if so, inventory is incremented with an `INBOUND` stock transaction.
