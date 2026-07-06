from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ARCHITECTURE_DIR = PROJECT_ROOT / "docs" / "architecture"


FILES = {
    "system_overview.md": """# System Overview

## Project Name

AI-Assisted Miniature Painting Recommendation System

## Purpose

This project helps miniature painters manage paint data, track owned paints, load painting workflows, generate recommendations, suggest substitutions, and create shopping lists.

The system started as a paint database, but it is now becoming a recommendation engine built around paint registries, inventory, and painting workflows.

## Major Components

- Paint Registry
- Registry Loader
- Inventory System
- Workflow Catalog
- Workflow Loader
- Workflow Validator
- Workflow Manager
- Recommendation Engine
- Substitution Engine
- Shopping List Generator

## Architecture Goal

Each module should have one clear responsibility.

The system should avoid duplicated file-loading logic, hardcoded paths, and mixed responsibilities.

## Current Phase

The project is moving from data foundation into application logic.
""",

    "workflow_system.md": """# Workflow System

## Purpose

The workflow system stores and loads painting instructions for specific factions, units, and model areas.

A workflow represents a repeatable painting recipe.

## Main Workflow Files

- `data/workflow_catalog/workflow_catalog.csv`
- `data/workflow_templates/workflow_template.csv`
- `data/workflows/`

## Workflow Catalog

The workflow catalog acts as the index for all available workflows.

It should include information such as:

- Workflow_ID
- Superfaction
- Faction
- Unit
- Workflow_File
- Status
- Notes

## Workflow Template

The workflow template defines the required schema for individual workflow CSV files.

Expected columns:

- Workflow_ID
- Superfaction
- Faction
- Unit
- Model_Area
- Area_Order
- Step_Order
- Technique
- Paint_ID
- Paint_Name
- Purpose
- Optional
- Notes

## Workflow Loader

The workflow loader is responsible for:

- Loading the workflow catalog
- Searching workflows by ID, faction, or unit
- Loading the actual workflow CSV
- Returning workflow data as a pandas DataFrame

The loader should not validate paint accuracy, check inventory, or make recommendations.
""",

    "recommendation_pipeline.md": """# Recommendation Pipeline

## Purpose

The recommendation pipeline connects workflows, inventory, substitutions, and shopping lists.

## Basic Flow

1. User selects or searches for a faction/unit.
2. Workflow Manager requests the matching workflow.
3. Workflow Loader loads the workflow CSV.
4. Workflow Validator checks that the workflow is usable.
5. Inventory system compares required paints against owned paints.
6. Substitution Engine suggests alternatives for missing paints.
7. Recommendation Engine produces the final recommendation.
8. Shopping List Generator lists missing paints.

## Responsibility Breakdown

### Workflow Loader

Loads workflow files.

### Workflow Validator

Checks that workflow data is valid.

### Workflow Manager

Provides a clean interface for workflow access.

### Inventory System

Tracks owned paints, quantities, and wishlist status.

### Substitution Engine

Finds usable alternatives for missing paints.

### Recommendation Engine

Coordinates the full recommendation process.

### Shopping List Generator

Outputs missing required paints.

## Design Principle

The recommendation engine should coordinate the system, not do every job itself.
""",

    "data_flow.md": """# Data Flow

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
"""
}


def create_architecture_docs():
    ARCHITECTURE_DIR.mkdir(parents=True, exist_ok=True)

    for filename, content in FILES.items():
        file_path = ARCHITECTURE_DIR / filename

        if file_path.exists():
            print(f"SKIPPED existing file: {file_path}")
            continue

        file_path.write_text(content, encoding="utf-8")
        print(f"CREATED: {file_path}")


if __name__ == "__main__":
    print("=" * 50)
    print("Creating architecture documentation")
    print("=" * 50)

    create_architecture_docs()

    print("=" * 50)
    print("Done")
    print("=" * 50)