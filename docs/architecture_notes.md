# Architecture Notes

## Architecture Philosophy

Registry tables answer:

"What paints exist?"

Future systems answer:

- Inventory
- Equivalents
- Triads
- Recommendations
- Workflows

Relationship data is intentionally separated from registry data.

## Data Flow

Manufacturer Registries
        ↓
Registry Loader
        ↓
Master DataFrame
        ↓
PaintDatabase
        ↓
Search
Swatches
Inventory
Recommendations

## Registry Loader

Loads all manufacturer registries.

Uses pandas.read_csv() to load data.

Uses pandas.concat() to create a single master DataFrame.

## Current Registries

- Games Workshop
- Army Painter
- Vallejo
- AK Interactive
- Pro Acryl

## Future Expansion

- SQLite
- Inventory tracking
- Recommendation engine
- Color matching
- Tkinter UI
- AI-assisted recommendations