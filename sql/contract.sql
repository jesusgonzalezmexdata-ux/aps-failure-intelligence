-- Data contract for the Scania APS training set (DuckDB).
-- Each check is one query returning a single boolean column `ok` and a `detail` value.
-- The holdout view exposes row count and column names only; its labels are never queried.

-- name: train_rows
SELECT count(*) = 60000 AS ok, count(*) AS detail FROM train;

-- name: train_columns
SELECT count(*) = 171 AS ok, count(*) AS detail
FROM (DESCRIBE train);

-- name: class_domain
SELECT bool_and(class IN ('pos', 'neg')) AS ok, string_agg(DISTINCT class, ',' ORDER BY class) AS detail FROM train;

-- name: positive_count
SELECT count(*) FILTER (WHERE class = 'pos') = 1000 AS ok,
       count(*) FILTER (WHERE class = 'pos') AS detail FROM train;

-- name: features_numeric
SELECT bool_and(column_type IN ('DOUBLE', 'BIGINT', 'INTEGER', 'HUGEINT')) AS ok,
       count(*) FILTER (WHERE column_type NOT IN ('DOUBLE', 'BIGINT', 'INTEGER', 'HUGEINT')) AS detail
FROM (DESCRIBE train) WHERE column_name <> 'class';

-- name: features_non_negative
WITH long AS (UNPIVOT (SELECT * EXCLUDE (class) FROM train) ON COLUMNS(*) INTO NAME feature VALUE v)
SELECT min(v) >= 0 AS ok, min(v) AS detail FROM long;

-- name: missing_rate_bounded
SELECT max(null_percentage) < 85 AS ok, max(null_percentage)::DOUBLE AS detail
FROM (SUMMARIZE train) WHERE column_name <> 'class';

-- name: single_constant_feature
WITH long AS (UNPIVOT (SELECT * EXCLUDE (class) FROM train) ON COLUMNS(*) INTO NAME feature VALUE v),
spread AS (SELECT feature, count(DISTINCT v) AS n FROM long GROUP BY feature)
SELECT count(*) FILTER (WHERE n <= 1) = 1 AS ok, string_agg(feature, ',') FILTER (WHERE n <= 1) AS detail FROM spread;

-- name: histogram_bins_complete
WITH cols AS (SELECT column_name FROM (DESCRIBE train) WHERE regexp_matches(column_name, '^[a-z]{2}_00[0-9]$')),
fam AS (SELECT left(column_name, 2) AS f, count(*) AS bins FROM cols GROUP BY f)
SELECT count(*) FILTER (WHERE bins = 10) = 7 AS ok, string_agg(f, ',' ORDER BY f) FILTER (WHERE bins = 10) AS detail FROM fam;

-- name: holdout_rows
SELECT count(*) = 16000 AS ok, count(*) AS detail FROM holdout_schema;

-- name: holdout_same_columns
SELECT (SELECT list(column_name ORDER BY column_name) FROM (DESCRIBE train) WHERE column_name <> 'class')
     = (SELECT list(column_name ORDER BY column_name) FROM (DESCRIBE holdout_schema)) AS ok,
       (SELECT count(*) FROM (DESCRIBE holdout_schema)) AS detail;
