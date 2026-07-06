SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS paints (
    paint_id TEXT PRIMARY KEY,
    company TEXT,
    brand TEXT,
    product_line TEXT,
    paint_name TEXT NOT NULL,
    hex TEXT,
    rgb TEXT,
    paint_type TEXT,
    status TEXT,
    source TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS inventory (
    paint_id TEXT PRIMARY KEY,
    owned INTEGER DEFAULT 0,
    wishlist INTEGER DEFAULT 0,
    qty INTEGER DEFAULT 0,
    FOREIGN KEY (paint_id) REFERENCES paints(paint_id)
);

CREATE TABLE IF NOT EXISTS workflows (
    workflow_id TEXT PRIMARY KEY,
    superfaction TEXT,
    faction TEXT,
    subfaction TEXT,
    army TEXT,
    unit TEXT,
    character TEXT,
    classification TEXT,
    painter TEXT,
    video_title TEXT,
    youtube_url TEXT,
    workflow_file TEXT,
    status TEXT,
    verified INTEGER DEFAULT 0,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS workflow_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_id TEXT NOT NULL,
    area_order INTEGER,
    step_order INTEGER,
    model_area TEXT,
    technique TEXT,
    paint_id TEXT,
    paint_name TEXT,
    paint_type TEXT,
    purpose TEXT,
    optional INTEGER DEFAULT 0,
    notes TEXT,
    FOREIGN KEY (workflow_id) REFERENCES workflows(workflow_id),
    FOREIGN KEY (paint_id) REFERENCES paints(paint_id)
);

CREATE TABLE IF NOT EXISTS techniques (
    technique TEXT PRIMARY KEY,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS import_files (
    file_hash TEXT PRIMARY KEY,
    file_name TEXT,
    file_path TEXT,
    file_type TEXT,
    import_date TEXT,
    status TEXT,
    workflow_id TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS review_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file TEXT,
    workflow_id TEXT,
    issue_type TEXT,
    issue_detail TEXT,
    status TEXT DEFAULT 'Open',
    created_at TEXT,
    resolved_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_workflow_steps_workflow_id
ON workflow_steps(workflow_id);

CREATE INDEX IF NOT EXISTS idx_workflow_steps_paint_id
ON workflow_steps(paint_id);

CREATE INDEX IF NOT EXISTS idx_workflows_faction_unit
ON workflows(faction, unit);

CREATE INDEX IF NOT EXISTS idx_paints_name
ON paints(paint_name);
"""
