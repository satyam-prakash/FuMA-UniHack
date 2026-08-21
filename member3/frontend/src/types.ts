/**
 * TypeScript mirrors of the Member 3 API responses.
 * Shapes verified against member3/backend/{routes/api.py,services/*}.
 */

export type JobStatus =
  | 'uploaded'
  | 'queued'
  | 'processing'
  | 'completed'
  | 'completed_with_review'
  | 'failed'
  | 'exported';

export type RowStatus = 'success' | 'review' | 'error';

export type ReviewAction = 'approve' | 'reject' | 'override' | 'mark_reviewed';

/** Exact literals the pipeline emits; drive the review filter chips. */
export type ReviewCategory =
  | 'low_confidence'
  | 'schema_failure'
  | 'no_attributes'
  | 'generic_taxonomy'
  | 'description_issue'
  | 'export_issue'
  | 'processing_error';

export const TERMINAL_STATUSES: readonly JobStatus[] = [
  'completed',
  'completed_with_review',
  'failed',
  'exported',
];

export interface Health {
  status: string;
  service: string;
  delivery_columns: number;
}

export interface UploadResult {
  job_id: string;
  filename: string;
  rows: number;
  status: JobStatus;
}

export interface EnrichResult {
  job_id: string;
  status: JobStatus;
}

export interface Job {
  job_id: string;
  filename: string;
  status: JobStatus;
  total: number;
  processed: number;
  success: number;
  review: number;
  errors: number;
  progress: number;
  elapsed_seconds: number;
}

export interface Attribute {
  label: string;
  value: string;
  uom: string;
}

export interface Enriched {
  mfg_part_num: string;
  part_desc_raw: string;
  manufacturer_name: string;
  brand_name: string;
  series: string;
  classpath: string;
  unspsc: string;
  product_name: string;
  attributes: Attribute[];
  features: string[];
  invoice_desc: string;
  mobile_desc: string;
  short_desc: string;
  long_desc1: string;
  retail_desc: string;
  confidence_score: number;
  needs_review: boolean;
  review_reasons: string[];
}

export interface Validation {
  schema_valid: boolean;
  schema_errors: string[];
  invoice_len: number;
  invoice_char_pass: boolean;
  invoice_caps: boolean;
  invoice_pass: boolean;
  mobile_len: number;
  /** <= 85: the limit ProductRecord actually enforces. */
  schema_mobile_pass: boolean;
  /** 60-80: the stricter client target. Never conflate with the above. */
  mobile_target_pass: boolean;
  attribute_count: number;
  feature_count: number;
  generic_classpath: boolean;
  export_warnings: string[];
}

export interface ReviewState {
  needs_review: boolean;
  reasons: string[];
  categories: ReviewCategory[];
  decision: ReviewAction | null;
  comment: string;
}

export interface RowError {
  code: string;
  message: string;
  stage: string;
}

export interface RowResult {
  row_id: number;
  status: RowStatus;
  /** Flattened conveniences the API adds for table rendering. */
  mpn: string;
  part_desc: string;
  brand_name: string;
  product_name: string;
  classpath: string;
  confidence_score: number;
  confidence: number;
  raw: Record<string, string>;
  /** M1 output: only the keys stage 1 added. */
  normalized: Record<string, string | number | boolean | null>;
  /** `{}` when a stage blew up, so every field is optional. */
  enriched: Partial<Enriched>;
  /** The mapped 252-column delivery row; null when the row errored. */
  delivery_row: Record<string, string> | null;
  validation: Validation;
  review: ReviewState;
  error: RowError | null;
}

export interface RowDetail extends RowResult {
  ground_truth: Record<string, string> | null;
}

export interface ResultsPage {
  page: number;
  page_size: number;
  total: number;
  rows: RowResult[];
}

export interface BenchmarkField {
  field: string;
  compared: number;
  exact_match_rate: number;
  normalized_match_rate: number;
}

export interface Benchmark {
  ground_truth_rows: number;
  matched_rows: number;
  fields: BenchmarkField[];
  overall_normalized_match_rate: number;
}

export interface Metrics {
  total: number;
  success: number;
  review: number;
  errors: number;
  success_rate: number;
  avg_confidence: number;
  invoice_char_pass: number;
  invoice_caps_pass: number;
  schema_mobile_pass: number;
  mobile_target_60_80_pass: number;
  schema_pass_rate: number;
  classpath_specific_rate: number;
  attribute_coverage: number;
  avg_attributes: number;
  confidence_histogram: { bucket: string; count: number }[];
  review_reasons: { reason: string; count: number }[];
  status_distribution: { status: string; count: number }[];
  benchmark: Benchmark | null;
  elapsed_seconds: number;
  delivery_columns: number;
}

export interface ExportStatus {
  delivery_columns: number;
  valid: boolean;
  errors: string[];
  row_count: number;
  rows_needing_review: number;
}

/** Columns the uploaded file must carry before enrichment can start. */
export const REQUIRED_INPUT_COLUMNS = [
  'Mfg_Part_Num',
  'Part_Desc',
  'E1_Brand',
  'Unilog_Brand',
  'DIB_Brand',
  'Part_Manuf',
] as const;

/** Character limits each generated description is judged against. */
export const DESCRIPTION_LIMITS = {
  invoice_desc: 40,
  mobile_desc: 85,
  short_desc: 120,
  long_desc1: 1000,
  retail_desc: 500,
} as const;

export type DescriptionKey = keyof typeof DESCRIPTION_LIMITS;

/** Blank record so screens can read fields off an errored row without guards. */
export const EMPTY_ENRICHED: Enriched = {
  mfg_part_num: '',
  part_desc_raw: '',
  manufacturer_name: '',
  brand_name: '',
  series: '',
  classpath: '',
  unspsc: '',
  product_name: '',
  attributes: [],
  features: [],
  invoice_desc: '',
  mobile_desc: '',
  short_desc: '',
  long_desc1: '',
  retail_desc: '',
  confidence_score: 0,
  needs_review: false,
  review_reasons: [],
};

/** Errored rows carry `enriched: {}`; fill the gaps instead of guarding at every read. */
export function enrichedOf(row: { enriched: Partial<Enriched> } | null | undefined): Enriched {
  return { ...EMPTY_ENRICHED, ...(row?.enriched ?? {}) };
}
