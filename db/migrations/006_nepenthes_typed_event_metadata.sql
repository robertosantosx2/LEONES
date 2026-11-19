-- NEPENTHES engine event schema v1.1: queryable typed metadata.
ALTER TABLE nepenthes_events ADD COLUMN correlation_token INTEGER;
ALTER TABLE nepenthes_events ADD COLUMN attribution_level TEXT;
ALTER TABLE nepenthes_events ADD COLUMN backend TEXT;
ALTER TABLE nepenthes_events ADD COLUMN memory_kind TEXT;
ALTER TABLE nepenthes_events ADD COLUMN memcpy_kind TEXT;
ALTER TABLE nepenthes_events ADD COLUMN raw_memcpy_kind INTEGER;
ALTER TABLE nepenthes_events ADD COLUMN sync_type TEXT;
ALTER TABLE nepenthes_events ADD COLUMN kv_op TEXT;

INSERT OR IGNORE INTO schema_migrations(version)
VALUES ('006_nepenthes_typed_event_metadata');
