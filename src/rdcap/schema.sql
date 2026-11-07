-- Relational model of the R&D data (designed with the domain experts in a real project)
DROP VIEW IF EXISTS v_trial_summary;
DROP TABLE IF EXISTS measurement;
DROP TABLE IF EXISTS formulation_line;
DROP TABLE IF EXISTS trial;
DROP TABLE IF EXISTS study;
DROP TABLE IF EXISTS component;
DROP TABLE IF EXISTS source_file;
DROP TABLE IF EXISTS issue;

CREATE TABLE source_file (
    file_id     INTEGER PRIMARY KEY,
    path        TEXT UNIQUE NOT NULL,
    template    TEXT NOT NULL,
    status      TEXT NOT NULL            -- loaded / duplicate / not_recognised
);

CREATE TABLE study (
    study_id           TEXT PRIMARY KEY,
    title              TEXT,
    objective          TEXT,
    author             TEXT,
    study_date         TEXT,
    gel_temperature_c  REAL,
    gel_time_min       REAL,
    file_id            INTEGER REFERENCES source_file(file_id)
);

CREATE TABLE component (
    component_id   TEXT PRIMARY KEY,     -- canonical name, e.g. DINP
    component_type TEXT                  -- resine / plastifiant / stabilisant / charge
);

CREATE TABLE trial (
    trial_id    TEXT PRIMARY KEY,
    study_id    TEXT REFERENCES study(study_id),
    trial_date  TEXT,
    operator    TEXT,
    file_id     INTEGER REFERENCES source_file(file_id)
);

CREATE TABLE formulation_line (
    trial_id      TEXT REFERENCES trial(trial_id),
    component_id  TEXT REFERENCES component(component_id),   -- NULL if not recognised
    component_raw TEXT NOT NULL,                              -- name as written in the file
    quantity_phr  REAL,
    source_cell   TEXT                                        -- traceability
);

CREATE TABLE measurement (
    trial_id     TEXT REFERENCES trial(trial_id),
    property     TEXT,                  -- normalized property name
    value        REAL,                  -- value in the reference unit
    unit         TEXT,                  -- reference unit
    value_raw    TEXT,                  -- value as written
    unit_raw     TEXT,                  -- unit as written
    source_cell  TEXT                   -- traceability
);

CREATE TABLE issue (                    -- everything the pipeline could not handle cleanly
    category   TEXT,
    severity   TEXT,
    detail     TEXT,
    source     TEXT
);

CREATE INDEX ix_trial_study ON trial(study_id);
CREATE INDEX ix_formulation_trial ON formulation_line(trial_id);
CREATE INDEX ix_measurement_trial ON measurement(trial_id);
CREATE INDEX ix_measurement_property ON measurement(property);

-- Convenient view: one row per trial with the main properties side by side
CREATE VIEW v_trial_summary AS
SELECT
    t.trial_id, t.study_id, s.title AS study_title, t.trial_date, t.operator,
    MAX(CASE WHEN c.component_type = 'plastifiant' THEN f.component_id END)  AS plasticizer,
    MAX(CASE WHEN c.component_type = 'plastifiant' THEN f.quantity_phr END)  AS plasticizer_phr,
    MAX(CASE WHEN c.component_type = 'stabilisant' THEN f.quantity_phr END)  AS stabilizer_phr,
    COALESCE(MAX(CASE WHEN c.component_type = 'charge' THEN f.quantity_phr END), 0) AS filler_phr,
    (SELECT value FROM measurement m WHERE m.trial_id = t.trial_id AND m.property = 'viscosite_1h')        AS viscosite_1h,
    (SELECT value FROM measurement m WHERE m.trial_id = t.trial_id AND m.property = 'viscosite_24h')       AS viscosite_24h,
    (SELECT value FROM measurement m WHERE m.trial_id = t.trial_id AND m.property = 'durete_shore_a')      AS durete_shore_a,
    (SELECT value FROM measurement m WHERE m.trial_id = t.trial_id AND m.property = 'stabilite_thermique') AS stabilite_thermique,
    sf.path AS source_file
FROM trial t
LEFT JOIN study s           ON s.study_id = t.study_id
LEFT JOIN formulation_line f ON f.trial_id = t.trial_id
LEFT JOIN component c       ON c.component_id = f.component_id
LEFT JOIN source_file sf    ON sf.file_id = t.file_id
GROUP BY t.trial_id;
