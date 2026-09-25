# Equipment App (Equipment Management Module)

## Description
The Equipment module manages production equipment in the factory, including equipment categorization, status monitoring, and maintenance history records.

## Models
* **EquipmentCategory**: Used to distinguish different equipment categories, such as "Lamination Equipment", "Inspection Equipment", etc.
* **Equipment**: Manages equipment ID (unique), name, category, location, purchase date, and current status.
  * Equipment status choices: Operational (`active`), Under Maintenance (`maintenance`), Faulty (`broken`), Retired (`retired`).
* **MaintenanceRecord**: Records detailed information about equipment maintenance and repairs, including maintenance type, fault cause, solution, labor hours, maintenance cost, and operator.

## Key Features & Logic
* **Equipment Status Transitions & History Tracking**: Provides intuitive interfaces to update equipment status and records background information for each status change and maintenance event.
* **Production Workflow Interlock (Poka-Yoke)**: Equipment operational status is tied to the Production module. When a work order process step requires a specific piece of equipment and its status is not `active`, the system prevents track-in/start.

## Change Notice
* Added safety status verification with the `Production` module process step track-in (non-active equipment blocks work order starting).
