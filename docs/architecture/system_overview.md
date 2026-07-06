# System Overview

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
