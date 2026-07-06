# Recommendation Pipeline

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
