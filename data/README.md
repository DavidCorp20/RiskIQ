# RiskIQ Data Layer

The Data Layer transforms institution-specific source data into the RiskIQ canonical portfolio model.

## Initial sources

- CSV
- Excel

## Future sources

- PostgreSQL
- MySQL
- REST APIs
- Data warehouses
- Core lending systems

## Pipeline

```text
SOURCE
  ↓
DISCOVERY
  ↓
MAPPING
  ↓
TYPE NORMALIZATION
  ↓
QUALITY VALIDATION
  ↓
CANONICAL MODEL
  ↓
PORTFOLIO SNAPSHOT
```

## Data quality dimensions

- completeness
- validity
- uniqueness
- consistency
- timeliness
- referential integrity

The ingestion process must report quality problems rather than silently modifying important financial values.
