# Data Flow

## Paint Data

Paint data begins in manufacturer registries.

Current registry structure:

- GW_registry.xlsx
- Army_Painter_registry.xlsx
- Vallejo_registry.xlsx
- AK_Interactive_registry.xlsx
- Pro_Acryl_registry.xlsx

These registries are loaded into a master paint database.

## Inventory Data

Inventory tracks which paints the user owns, wants, or needs.

Inventory should reference Paint_ID values from the master paint database.

## Workflow Data

Workflow data references paints by Paint_ID and Paint_Name.

The Paint_ID is the most important connection point between workflows, registries, inventory, substitutions, and shopping lists.

## High-Level Flow

Paint Registries
    ↓
Registry Loader
    ↓
Master Paint Database
    ↓
Inventory System
    ↓
Workflow Catalog
    ↓
Workflow Loader
    ↓
Workflow Validator
    ↓
Recommendation Engine
    ↓
Substitution Engine
    ↓
Shopping List Generator

## Key Rule

Paint_ID should remain the primary identifier across the system.

Paint_Name is useful for humans, but Paint_ID is safer for code.
