# AI Miniature Painting Assistant

## Overview

The AI Miniature Painting Assistant is a software development project focused on helping miniature painters select paints, find cross-brand color equivalents, manage inventory, and receive painting recommendations.

This project is being developed as part of a Software Development internship and serves as a portfolio project demonstrating:

* Python development
* Data management
* GUI design
* AI integration
* Software architecture
* Recommendation systems
* Containerization

## Current Project Status

Current Development Phase: MVP Development

Completed:

* Registry-first architecture design
* Paint database schema design
* Multi-registry loading system
* Master DataFrame generation
* Search system
* Data auditing tools
* Docker containerization
* Podman containerization support

Current Database Statistics:

* Total Paint Records: 1,987
* Manufacturers Supported: 5

Supported Manufacturers:

* Games Workshop / Citadel
* Army Painter
* Vallejo
* AK Interactive
* Monument Hobbies / Pro Acryl

## Current Architecture

Manufacturer Registries

* Games Workshop Registry
* Army Painter Registry
* Vallejo Registry
* AK Interactive Registry
* Pro Acryl Registry

Registry CSV Files
↓
Registry Loader
↓
Master DataFrame
↓
Paint Database
↓
Search
Swatches
Inventory
Recommendations

Registry tables are responsible only for storing paint information.

Relationship systems such as equivalents, recommendations, workflows, and inventory tracking are intentionally separated from registry data.

## Planned Features

### MVP

* Paint database
* Cross-brand paint equivalents
* Inventory tracking
* Recommendation engine
* Workflow suggestions
* Basic Tkinter user interface

### Future Features

* SQLite database migration
* Advanced color matching
* Image analysis
* AI painting assistant
* Recipe generation
* Cloud synchronization

## Technology Stack

Current:

* Python
* pandas
* Tkinter
* Excel
* Docker
* Podman

Planned:

* SQLite
* AI-assisted recommendation systems

## Running the Project

Main Application:

python main.py

Database Audit:

python -m src.audit

Install Requirements:

pip install -r requirements.txt

Build Docker Container:

docker build --load -t ai-miniature-painting-assistant .

Run Docker Container:

docker run --rm ai-miniature-painting-assistant

## Adjustments to be Made Later

### Paint ID Naming

Current Paint_ID values include manufacturer and product line information.

Example:

GW_BASE_MACRAGGE_BLUE

Future versions may use a revised naming convention.

### Color Family Searching

Future search functionality should include Color_Family searching.

Current implementation performs name-based searches.

Example:

Searching for "blue" currently finds paints containing the word "blue" in the paint name.

Future versions should return visually blue paints even when "blue" is not present in the paint name.

## Known Data Limitations

### Hex/RGB Audit Results

Missing Hex Values: 408

Breakdown:

* Army Painter: 371
* Vallejo: 33
* Games Workshop: 4

Most missing Army Painter values are located within:

* Fanatic
* Air
* Speedpaint

Database architecture, registry loading, search functionality, and schema validation are functioning correctly.

Missing color data will be addressed during future registry auditing and data enrichment phases.
