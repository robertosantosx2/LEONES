BEGIN IMMEDIATE;

ALTER TABLE nsys_activities ADD COLUMN attributed_batch_token INTEGER;
ALTER TABLE nsys_activities ADD COLUMN batch_attribution_level TEXT;
ALTER TABLE nsys_activities ADD COLUMN batch_attribution_status TEXT NOT NULL DEFAULT 'unattributed';
ALTER TABLE nsys_activities ADD COLUMN nvtx_marker_scope TEXT;

ALTER TABLE nepenthes_nsys_activities ADD COLUMN attributed_batch_token INTEGER;
ALTER TABLE nepenthes_nsys_activities ADD COLUMN batch_attribution_level TEXT;
ALTER TABLE nepenthes_nsys_activities ADD COLUMN batch_attribution_status TEXT NOT NULL DEFAULT 'unattributed';
ALTER TABLE nepenthes_nsys_activities ADD COLUMN nvtx_marker_scope TEXT;

CREATE INDEX IF NOT EXISTS idx_nsys_activities_attributed_batch
    ON nsys_activities(import_id, attributed_batch_token, batch_attribution_level);
CREATE INDEX IF NOT EXISTS idx_nsys_only_activities_attributed_batch
    ON nepenthes_nsys_activities(import_id, attributed_batch_token, batch_attribution_level);

-- One batch token can contain multiple request/task members, and one batch
-- window can contain multiple GPU activities. This view intentionally expands
-- that many-to-many relation; it never picks a single request for shared work.
CREATE VIEW IF NOT EXISTS nepenthes_batch_activity_membership AS
SELECT
    a.import_id,
    e.run_id,
    a.activity_id,
    a.activity_kind,
    a.start_ns,
    a.end_ns,
    a.attributed_batch_token AS correlation_token,
    a.batch_attribution_level,
    a.batch_attribution_status,
    e.event_id AS member_event_id,
    e.request_id,
    e.value0 AS slot_id,
    e.value1 AS task_id
FROM nsys_activities AS a
JOIN nepenthes_events AS e
  ON e.import_id = a.import_id
 AND e.correlation_token = a.attributed_batch_token
WHERE a.attributed_batch_token IS NOT NULL
  AND a.activity_kind IN ('cuda_kernel', 'cuda_memcpy', 'cuda_memset')
  AND e.event_kind = 'routing'
  AND e.label = 'server.batch_member';

CREATE VIEW IF NOT EXISTS nepenthes_nsys_batch_activity_membership AS
SELECT
    a.import_id,
    e.run_id,
    a.activity_id,
    a.activity_kind,
    a.start_ns,
    a.end_ns,
    a.attributed_batch_token AS correlation_token,
    a.batch_attribution_level,
    a.batch_attribution_status,
    e.event_id AS member_event_id,
    e.request_id,
    e.value0 AS slot_id,
    e.value1 AS task_id
FROM nepenthes_nsys_activities AS a
JOIN nepenthes_events AS e
  ON e.import_id = a.import_id
 AND e.correlation_token = a.attributed_batch_token
WHERE a.attributed_batch_token IS NOT NULL
  AND a.activity_kind IN ('cuda_kernel', 'cuda_memcpy', 'cuda_memset')
  AND e.event_kind = 'routing'
  AND e.label = 'server.batch_member';

INSERT OR IGNORE INTO schema_migrations(version)
VALUES ('007_nepenthes_batch_attribution');

COMMIT;
