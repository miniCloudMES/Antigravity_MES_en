# Dashboard App (Home & Dashboard Module)

## Description
The Dashboard module serves as the entry portal for the system. It provides a system landing page for unauthenticated visitors and an integrated real-time monitoring and analytics dashboard for authenticated MES users.

## Key Features & Logic
* **LandingPageView**: System landing page featuring module overviews and login navigation.
* **DashboardView**: Core statistical dashboard aggregating and summarizing:
  * **Production Data**: Daily work order counts, in-progress work orders, and completion rates.
  * **Equipment Status**: Proportional statistics for running, maintenance, and faulty equipment.
  * **Inventory Alerts**: Real-time alerts for materials below safety stock levels.
  * **Document Status**: Tracking and statistics for documents awaiting review/approval.

## Change Notice
* Added low stock real-time alerts and pending review document counters.
