# Workflow System

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
