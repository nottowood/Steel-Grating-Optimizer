# SGO v1.1.0-RC1

## New Features

### Phase-3 Material Recovery Engine

Added:

* Reusable Strip Inventory
* Scrap Classification
* Manufacturing Compatibility Key (MCK)
* Expansion Matching Engine
* Recovery KPI Engine
* Recovery Validation Engine
* Recovery Reporting
* Explainability Layer

### Recovery KPIs

Added:

* Recovery Rate
* Recovered Area
* Stock Utilization Rate
* Material Recovery Score
* Remaining Inventory Area
* Dead Scrap Area

### Validation

Added:

* R10-R21 Validation Rules
* Recovery Bounds Validation
* Frozen KPI Protection

### UI

Added:

* Recovery Status
* Scrap Inventory
* Recovery Matching
* Recovery Validation
* Recovery Explainability

## Compatibility

* Fully backward compatible with v1.0.0-FROZEN
* Frozen Yield unchanged
* Frozen Ranking unchanged
* Frozen Scoring unchanged
* Frozen Warnings unchanged

## Known Technical Debt

* TD-002 MCK Normalization
* TD-003 EXACT_FIT Classification
* TD-005 ProductMaster Extension (Deferred)
