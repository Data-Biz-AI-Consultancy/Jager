-- Dynamic consolidated view across all s_manual ingestion tables
CREATE OR REPLACE FUNCTION s_manual.refresh_manual_records_view()
RETURNS void AS $$
DECLARE
  sql_query text := '';
  rec record;
BEGIN
  FOR rec IN (
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 's_manual' 
      AND table_type = 'BASE TABLE' 
      AND table_name NOT LIKE '\_dlt%'
  ) LOOP
    IF sql_query != '' THEN
      sql_query := sql_query || ' UNION ALL ';
    END IF;
    sql_query := sql_query || 'SELECT ''' || rec.table_name || ''' AS source_table, to_jsonb(t.*) AS payload FROM s_manual.' || quote_ident(rec.table_name) || ' t';
  END LOOP;

  IF sql_query != '' THEN
    EXECUTE 'CREATE OR REPLACE VIEW s_manual.v_manual_records AS ' || sql_query;
  ELSE
    EXECUTE 'CREATE OR REPLACE VIEW s_manual.v_manual_records AS SELECT ''''::text AS source_table, ''{}''::jsonb AS payload WHERE false';
  END IF;
END $$ LANGUAGE plpgsql;

SELECT s_manual.refresh_manual_records_view();
