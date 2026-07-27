# AI Miniature Painting Assistant

<p align="center">

<img src="docs/images/app_icon.png" width="128">

**A Python desktop application for miniature painters featuring workflow exploration, paint management, inventory tracking, cross-brand paint matching, and intelligent recommendation tools.**

</p>

---

## Overview

The AI Miniature Painting Assistant is a desktop application designed to simplify miniature painting by bringing paint management, workflow organization, and paint recommendations together in a single interface.

Originally developed during a Software Development internship, the project evolved into a full-stack desktop application focused on backend architecture, structured data management, recommendation systems, and future AI-assisted painting guidance.

---

# Screenshots

## Workflow Explorer

![Workflow Explorer](docs/images/workflow_explorer.png)

![Workflow Screenshot](docs/images/workflow_screenshot.png)


Browse professionally organized painting workflows by superfaction, faction, subfaction, unit, and workflow style.

---

## Paint Browser & Recommendation Engine

![Paint Search and Matching](docs/images/searches_screenshot.png)

Search nearly 2,000 paints, compare manufacturers, preview colors, manage inventory, and discover similar paints using RGB-based matching.

---

## Inventory Manager

![Inventory](docs/images/inventory_screenshot.png)

Track owned paints and wishlist items while integrating inventory directly into recommendation workflows.

---

# Features

### Workflow Explorer

- Organized by Superfaction
- Faction navigation
- Subfaction support
- Unit selection
- Multiple workflow variants
- Step-by-step paint recipes
- Expandable workflow stages
- Workflow metadata panel

---

### Paint Browser

- Browse 1,984 paints
- Manufacturer filtering
- Product line filtering
- Paint type filtering
- Live search
- Dynamic paint icons
- Color previews
- Exact paint equivalents
- RGB similarity matching

---

### Inventory

- Owned paint tracking
- Wishlist tracking
- Inventory-aware recommendations
- Integrated with workflow system

---

### Recommendation System

- Exact equivalents
- Near matches
- Similarity percentages
- Cross-brand recommendations
- Registry-driven matching

---

### Backend

- SQLite database
- Registry import pipeline
- Data validation
- Audit tools
- Workflow database
- Registry normalization
- Modular architecture

---

# Supported Manufacturers

- Games Workshop (Citadel)
- Vallejo
- Army Painter
- AK Interactive
- Monument Hobbies (Pro Acryl)

---

# Technology Stack

Backend

- Python
- SQLite
- pandas
- openpyxl

Desktop

- Tkinter
- Pillow

Development

- Git
- GitHub
- Docker
- Podman

---

# Current Status

Current Version

**v2.1.8**

Completed

- Paint Registry
- SQLite Backend
- Workflow Explorer
- Paint Browser
- Inventory
- Recommendation Engine Foundation
- Paint Inspector
- Dynamic Paint Rendering
- Registry Auditing
- Import Pipeline
- Developer Tools

Future Development

- AI-assisted workflow recommendations
- Recipe generation
- Image recognition
- Additional manufacturers
- Community workflows

---

# Running

```powershell
python -m venv .venv

.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt

python main.py
```

---

# Why This Project Exists

Miniature painters often own paints from multiple manufacturers while following tutorials that use completely different paint ranges.

This application bridges that gap by combining:

- inventory tracking
- workflow management
- paint equivalency
- structured painting data
- recommendation logic

into one desktop application.

---

# License

MIT
