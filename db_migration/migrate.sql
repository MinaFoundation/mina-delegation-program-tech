BEGIN;

DROP TABLE uptime_file_history;

DROP TABLE bp_ip_address_2022_12;

DROP TABLE nodes_sidecar;

DROP TABLE points_summary;

--bot_logs:

DELETE FROM bot_logs
WHERE batch_start_epoch <= trunc(extract(epoch from ('2023-12-01 00:00:00+00' :: timestamp)));

ALTER TABLE bot_logs
DROP COLUMN status;

ALTER TABLE bot_logs
DROP COLUMN number_of_threads;

--nodes:

DELETE FROM nodes
WHERE updated_at IS NULL;

ALTER TABLE nodes
ALTER COLUMN updated_at SET NOT NULL;

ALTER TABLE nodes
ALTER COLUMN score_percent TYPE NUMERIC(10, 2);

-- points:

DELETE FROM points
WHERE bot_log_id IS NULL
OR node_id IS NULL
OR statehash_id IS NULL
OR bot_log_id NOT IN (SELECT id FROM bot_logs)
OR node_id NOT IN (SELECT id FROM nodes);

ALTER TABLE points
ALTER COLUMN node_id SET NOT NULL;

ALTER TABLE points
ALTER COLUMN bot_log_id SET NOT NULL;

ALTER TABLE points
ADD FOREIGN KEY (bot_log_id) REFERENCES bot_logs(id);

ALTER TABLE points
ADD FOREIGN KEY (node_id) REFERENCES nodes(id);

DROP TRIGGER trg_update_point_summary ON points;

-- bot_logs_statehash:

DELETE FROM bot_logs_statehash
WHERE bot_log_id IS NULL
OR statehash_id IS NULL
OR bot_log_id NOT IN (SELECT id FROM bot_logs);

ALTER TABLE bot_logs_statehash
ALTER COLUMN  statehash_id SET NOT NULL;

ALTER TABLE bot_logs_statehash
ALTER COLUMN  parent_statehash_id SET NOT NULL;

ALTER TABLE bot_logs_statehash
ALTER COLUMN  bot_log_id SET NOT NULL;

ALTER TABLE bot_logs_statehash
ADD FOREIGN KEY (bot_log_id) REFERENCES bot_logs(id);

ALTER TABLE bot_logs_statehash
ADD FOREIGN KEY (statehash_id) REFERENCES statehash(id);

ALTER TABLE bot_logs_statehash
ADD FOREIGN KEY (parent_statehash_id) REFERENCES statehash(id);

-- score_history:

DELETE FROM score_history
WHERE node_id IS NULL
OR node_id NOT IN (SELECT id FROM nodes);

ALTER TABLE score_history
ALTER COLUMN node_id SET NOT NULL;

ALTER TABLE score_history
ADD FOREIGN KEY (node_id) REFERENCES nodes(id);

ALTER TABLE score_history
ADD COLUMN id SERIAL PRIMARY KEY;

ALTER TABLE score_history
ALTER COLUMN score_percent TYPE NUMERIC(10, 2);

-- statehash

DELETE FROM statehash
WHERE id NOT IN (
  SELECT DISTINCT statehash_id
  FROM bot_logs_statehash
  WHERE statehash_id IS NOT NULL
  UNION
  SELECT DISTINCT parent_statehash_id
  FROM bot_logs_statehash
  WHERE parent_statehash_id IS NOT NULL
  UNION
  SELECT DISTINCT statehash_id
  FROM points
  WHERE statehash_id IS NOT NULL
);

COMMIT;
