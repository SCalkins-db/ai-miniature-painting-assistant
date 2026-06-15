# Database Schema

## Overview

The project currently uses a registry-first database design.

Each manufacturer registry stores paint product information only. Relationship data such as equivalents, triads, workflows, inventory, and recommendations will be stored separately in future project phases.

## Final Registry Schema

| Column | Description |
|---|---|
| Paint_ID | Unique identifier for each paint record |
| Company | Parent company or manufacturer |
| Brand | Paint brand name |
| Product_Line | Product line or paint range |
| Paint_Name | Official paint name |
| Hex | Hexadecimal color value |
| RGB | RGB color value |
| Paint_Type | Paint category or functional type |
| Status | Active, discontinued, legacy, or unknown status |
| Source | Data source used for the record |
| Notes | Additional audit or verification notes |

## Database Rules

- One paint equals one row.
- No duplicate records within Company + Product_Line + Paint_Name.
- Active and discontinued paints are preserved.
- Registry tables store paint data only.
- Relationship data is stored separately.
- Hex and RGB values are used for swatches and future color matching.
- Missing Hex/RGB values are tracked through audit tools.

## Current Record Count

Total Paint Records: 1,987

## Supported Companies

- AK Interactive
- Army Painter
- Games Workshop
- Monument Hobbies
- Vallejo

## Known Schema Notes

Current Paint_ID values may include company, product line, and paint name information.

Example:

```text
GW_BASE_MACRAGGE_BLUE