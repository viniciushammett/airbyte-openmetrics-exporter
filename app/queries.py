CONNECTION_STATUS = """
SELECT
  c.id::text AS connection_id,
  COALESCE(NULLIF(c.name, ''), c.id::text) AS connection_name,
  COALESCE(NULLIF(src.name, ''), 'unknown') AS source_name,
  COALESCE(NULLIF(dst.name, ''), 'unknown') AS destination_name,
  LOWER(COALESCE(c.status::text, 'unknown')) AS status
FROM connection c
LEFT JOIN actor src ON src.id = c.source_id
LEFT JOIN actor dst ON dst.id = c.destination_id
WHERE COALESCE(c.tombstone, false) = false
ORDER BY c.name NULLS LAST, c.id;
"""

RUNNING_JOBS = """
SELECT COUNT(*)::bigint AS running_jobs
FROM jobs
WHERE LOWER(status::text) IN ('running', 'pending', 'incomplete');
"""

JOB_COUNTS_24H = """
SELECT
  COUNT(*) FILTER (
    WHERE LOWER(status::text) = 'failed'
      AND COALESCE(updated_at, created_at) >= NOW() - INTERVAL '1 hour'
  )::bigint AS failed_last_1h,
  COUNT(*) FILTER (
    WHERE LOWER(status::text) = 'failed'
      AND COALESCE(updated_at, created_at) >= NOW() - INTERVAL '24 hours'
  )::bigint AS failed_last_24h,
  COUNT(*) FILTER (
    WHERE LOWER(status::text) = 'succeeded'
      AND COALESCE(updated_at, created_at) >= NOW() - INTERVAL '24 hours'
  )::bigint AS succeeded_last_24h,
  COUNT(*) FILTER (
    WHERE LOWER(status::text) = 'cancelled'
      AND COALESCE(updated_at, created_at) >= NOW() - INTERVAL '24 hours'
  )::bigint AS cancelled_last_24h
FROM jobs
WHERE COALESCE(updated_at, created_at) >= NOW() - INTERVAL '24 hours';
"""

SYNC_LAST_STATS = """
WITH latest_attempt AS (
  SELECT DISTINCT ON (j.config_id)
    j.config_id::text AS connection_id,
    COALESCE(NULLIF(c.name, ''), j.config_id::text) AS connection_name,
    COALESCE(NULLIF(src.name, ''), 'unknown') AS source_name,
    COALESCE(NULLIF(dst.name, ''), 'unknown') AS destination_name,
    LOWER(COALESCE(j.status::text, 'unknown')) AS job_status,
    COALESCE(a.created_at, j.created_at) AS started_at,
    COALESCE(a.updated_at, j.updated_at) AS finished_at,
    a.output::jsonb AS attempt_output
  FROM jobs j
  LEFT JOIN attempts a ON a.job_id = j.id
  LEFT JOIN connection c ON c.id::text = j.config_id::text
  LEFT JOIN actor src ON src.id = c.source_id
  LEFT JOIN actor dst ON dst.id = c.destination_id
  WHERE LOWER(j.scope::text) = 'sync'
    AND LOWER(j.config_type::text) = 'sync'
    AND COALESCE(c.tombstone, false) = false
  ORDER BY j.config_id, COALESCE(a.updated_at, j.updated_at) DESC NULLS LAST, j.id DESC
)
SELECT
  connection_id,
  connection_name,
  source_name,
  destination_name,
  job_status,
  GREATEST(EXTRACT(EPOCH FROM (finished_at - started_at))::double precision, 0) AS duration_seconds,
  COALESCE((attempt_output #>> '{sync,standardSyncOutput,totalStats,recordsCommitted}')::double precision, 0) AS records_committed,
  COALESCE((attempt_output #>> '{sync,standardSyncOutput,totalStats,recordsEmitted}')::double precision, 0) AS records_emitted,
  COALESCE((attempt_output #>> '{sync,standardSyncOutput,totalStats,bytesCommitted}')::double precision, 0) AS bytes_committed,
  COALESCE((attempt_output #>> '{sync,standardSyncOutput,totalStats,bytesEmitted}')::double precision, 0) AS bytes_emitted
FROM latest_attempt;
"""

DB_PING = "SELECT 1 AS ok;"
