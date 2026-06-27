# Enrichment Diagnostic Analysis

## Overall Summary

- Registries checked: 5
- Total registry rows: 1987
- Missing Hex/RGB rows checked: 337
- Auto-fill same company: 0
- Auto-fill equivalency: 0
- Needs review/manual work: 337

## Status Breakdown

| Status | Count |
|---|---:|
| MANUAL_RESEARCH | 301 |
| EQUIVALENCY_TARGET_MISSING_COLOR | 2 |
| UNSUPPORTED_EQUIVALENCY_COMPANY | 2 |
| SAME_COMPANY_MATCH_MISSING_COLOR | 32 |

## Missing Rows by Company

| Company | Count |
|---|---:|
| Army Painter | 300 |
| Games Workshop | 4 |
| Vallejo | 33 |

## Missing Rows by Product Line

| Product Line | Count |
|---|---:|
| Speedpaint | 17 |
| Air | 98 |
| Fanatic | 186 |
| Technical | 2 |
| Spray | 1 |
| Game Color Auxiliary | 2 |
| Game Color Metallic | 1 |
| Game Color Special FX | 4 |
| Model Air | 2 |
| Model Color | 20 |
| Model Color Related | 3 |
| Xpress Color | 1 |

## Recommended Workflow

1. Review `AUTO_FILL_SAME_COMPANY` rows first.
2. Review `AUTO_FILL_EQUIVALENCY` rows second.
3. Investigate `EQUIVALENCY_TARGET_MISSING_COLOR` rows because enriching those targets may unlock more rows.
4. Ignore or defer unsupported companies unless you add those manufacturers later.
5. Manually research remaining `MANUAL_RESEARCH` rows.
