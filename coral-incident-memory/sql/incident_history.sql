SELECT
  service_name,
  alert_id,
  severity,
  started_at,
  summary,
  rca,
  ticket_key,
  ticket_title,
  ticket_status,
  ticket_priority,
  owner_team,
  owner,
  resolution,
  customer_impact,
  follow_up
FROM local_incidents.incidents
WHERE service_name = :service_name
ORDER BY started_at DESC
LIMIT 5;