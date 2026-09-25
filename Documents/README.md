# Documents App (Document Management & Approval Workflow Module)

## Description
The Documents module provides centralized management for electronic documents (such as SOP work instructions, quality control standards, equipment manuals, etc.), integrating multi-image display, version control, and a formal **document submission and approval workflow**.

## Models
* **DocumentCategory**: Manages document categories, such as "Technical Documents", "SOP", "Management Systems", etc.
* **Document**: Stores document title, document code (unique), content description, current version (e.g., 1.0, 2.0), approval status (`draft` / `pending` / `approved` / `rejected`), submitted by, and approval manager.
* **DocumentImage**: Supports associating multiple images per document for displaying detailed diagrams or process steps.
* **DocumentAuditLog**: Records every action during the document lifecycle (create, submit for review, approve, reject, recall, toggle active) along with review comments and timestamps.

## Key Features & Logic
* **Strict Approval Workflow**:
  * Document lifecycle: `draft` → `pending` → `approved` or `rejected`.
  * **Automatic version bump on rejection**: If a document is rejected and subsequently resubmitted, the version number increments automatically (e.g., 1.0 to 1.1) for historical audit tracking.
* **Granular Access Control**:
  * Draft and rejected documents can only be edited or deleted by the author.
  * For pending documents, the author can recall the submission before review.
  * Approved documents become read-only for operators (`operator`), while `admin` or `manager` can make revisions or status updates.

## Change Notice
* Added document audit logging mechanism to ensure ISO compliance auditing.
