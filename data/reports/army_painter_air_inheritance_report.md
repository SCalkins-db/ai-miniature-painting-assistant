# Army Painter Air Inheritance Report

Input CSV: `C:\Users\DEVBOXSC\ai-miniature-painting-assistant\data\registries_csv\archive\Army_Painter_registry_26.0.11_aligned.csv`
Output CSV: `C:\Users\DEVBOXSC\ai-miniature-painting-assistant\data\registries_csv\Army_Painter_registry_26.0.16_air_inheritance_enriched.csv`
Output XLSX: `C:\Users\DEVBOXSC\ai-miniature-painting-assistant\data\registries_xlsx\Army_Painter_registry_26.0.16_air_inheritance_enriched.xlsx`

## Summary

- Air rows filled: 0
- Air rows needing review: 97
- Skipped non-Air rows: 306
- Skipped already-complete Air rows: 37

## Method

This script fills missing Hex/RGB for Army Painter Air rows by matching the Air paint name against completed non-Air Army Painter paints.

It only auto-fills when the matched main paint has usable Hex/RGB and there is no conflicting color value.