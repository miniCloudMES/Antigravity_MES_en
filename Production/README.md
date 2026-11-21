# Production App (Production & Work Order Module)

## Description
The Production module is the core of the whole MES system. It handles work order execution tracking, production routing, and the BOM relationships for finished goods, covering the full lifecycle from creating a work order, through shop-floor start-up, to material backflushing on completion.

## Models
* **WorkOrder**: Manages the work order number (unique), the finished product, the planned quantity, the work order status (pending, in progress, completed, cancelled, abnormal) and the planned/actual start and end dates.
* **BOM**: Bound one-to-one to a finished product; controls the BOM version and its active state.
* **BOMItem**: Records each raw material component in the BOM together with its per-unit quantity.
* **ProcessStep**: The product's standard process card; defines the sequence, name, process instructions, required position, equipment, material, reference documents and QC requirements for each step.
* **WorkOrderStep**: A snapshot copied automatically from the standard process when a work order is created, used by shop-floor operators for actual reporting and status changes.

## Key Features & Logic
* **Automatic status derivation**: the work order status is derived automatically from the latest progress of its steps (for example, once every step is complete the work order becomes completed).
* **Backflushing**: when a work order is completed, the required raw materials in the BOM are automatically matched against and deducted from stock.

---

## Change Notice - Major Improvements

This module recently received significant production-flow and safety improvements:

1. **Shop-floor poka-yoke guards**:
   * **Position skill matching**: if a step specifies a required position (e.g. QC inspector `pos_qa`), only an `operator` matching that position, or an `admin`/`manager` with management rights, may perform the action — preventing unauthorised cross-station reporting.
   * **Equipment fault lockout**: when starting a step the system validates the associated equipment status; if the equipment is in a non-active state such as `broken` or `maintenance`, start-up is blocked.
2. **Start-up readiness pre-check**:
   * When the first step of a work order starts and the work order is about to move to `IN_PROGRESS`, the system proactively runs a BOM material readiness check. If any material is short, start-up is blocked, avoiding a production line being forced to stop halfway.

3. **Precise step time tracking**:
   * Added the `actual_start_date` and `actual_end_date` fields to `WorkOrderStep`. Timestamps are filled in automatically on start and completion, making it easier to compute actual labour hours and run IE efficiency analysis.
4. **Automatic finished-goods inbound on completion**:
   * Once a work order is fully complete, besides deducting raw material stock, the system looks for a `Material` whose `product_id` matches the finished product, increases its stock automatically and writes an `INBOUND` stock transaction — closing the material-flow loop.

---

In an MES environment, the on-station work card display and the operator's specific actions are as follows:

## 1. Information the MES Station Work Card (Screen) Should Show

After an operator logs in at a station, the MES screen clearly displays the following three categories of real-time information:

> * **Work order and product status**:
  * **Production basics**: work order number (WO), product part number, product name, customer name.
  * **Batch status**: current lot ID, current station, previous station's completion time.
  * **Quantity statistics**: total quantity in line for this batch, quantity scanned in so far.
> * **Process control and error-proofing (Poka-Yoke)**:
  * **SOP hyperlink**: click to open the electronic standard operating procedure for the station.
  * **Parameter prompts**: the machine settings required for this part number (e.g. temperature, pressure, recipe number).
  * **Dedicated tooling list**: the mould/fixture numbers the system requires to be used.
> * **Quality control (SPC/QA)**:
  * **First-article status**: a system lockout light showing "first article pending", "first article passed" or "first article failed".
  * **Material issue/return control**: the raw materials and auxiliary materials that must be bound at this station.

---

## 2. The Operator's "Actions and Inputs" Flow in the MES

Operators do not write anything by hand; data is collected through three actions: **scan, select, tap**.

### 2.1 Track-In (Start)

> * **Scan identity**: the operator scans their own badge (employee number); the system automatically binds the responsible person and the start time.
> * **Scan work card / lot**: scan the barcode on the line basket or the product (Lot ID / Serial Number); the system **automatically checks** whether this batch has arrived at the wrong station (error-proofing).
> * **Bind equipment and tooling**: scan the current machine number and mould barcode. If the mould is past its life or not maintained, the system raises a warning and locks the machine.
> * **Material loading**: if this station has an assembly line, the lot IDs (Reel ID / Lot ID) of the raw materials being loaded must be scanned for traceability.

### 2.2 Processing and Inspection (Data Collection)

> * **First-article and measurement entry**: where sampling rules apply, the operator enters measurement data on screen (e.g. dimensions, weight).
  * *Note: if the gauge is connected (Bluetooth/RS232), values are filled in automatically and the operator only needs to tap "Confirm".*
> * **Calling an abnormality (Andon)**: if an equipment fault, material shortage or quality problem occurs during processing, the operator taps the "Call abnormality" button; the system notifies the engineer automatically and records the **downtime**.

### 2.3 Track-Out (Completion)

> * **Tap to complete**: when processing finishes, the system usually pulls the quantity automatically from the machine counter, or the operator taps to complete.
> * **Enter defect category and quantity**:
  * If there are defects, the operator taps a **defect code** on screen (e.g. A01 - cosmetic scratch, B03 - out-of-tolerance dimension).
  * Enter the corresponding NG quantity; the system deducts it automatically and routes it to the rework flow or the scrap store.
> * **Print and hand off**: once confirmed, tap submit; the system settles the station yield automatically and updates the pending list for the next station.

---

The core of an MES system is **real-time data** and **error-proofing**. If you would like the interface and the operator flow to run more smoothly, tell me:
