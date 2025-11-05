export type ManagedDatabase = {
  name: string;
  dsn: string;
  display_name?: string;
  description?: string;
  style_id?: string;
  is_active: boolean;
  last_import_job_id?: string;
  last_replication_job_id?: string;
  last_size_bytes?: number;
  last_checked_at?: string;
};

export type DatabaseStats = {
  name: string;
  size_bytes: number;
  table_count: number;
};

export type Job = {
  id: string;
  type: string;
  target_db?: string;
  status: string;
  started_at?: string;
  finished_at?: string;
  duration_ms?: number;
  params?: Record<string, unknown>;
  error_message?: string;
};

export type JobLogLine = {
  ts: string;
  line: string;
};

export type ReplicationConfig = {
  target_db: string;
  base_url: string;
  state_path: string;
  interval_minutes: number;
  dry_run: boolean;
  catch_up: boolean;
  last_sequence_number?: number;
  last_timestamp?: string;
};
