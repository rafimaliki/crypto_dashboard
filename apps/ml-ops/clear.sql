-- 1. Unlink Datasets from Runs (The 'inputs' table links runs to datasets)
DELETE FROM inputs 
WHERE source_id IN (SELECT dataset_uuid FROM datasets WHERE experiment_id = 3)
AND source_type = 'DATASET';

-- 2. Delete the Datasets metadata
DELETE FROM datasets WHERE experiment_id = 3;

-- 3. Delete Model Registry versions (If you promoted models from this experiment)
DELETE FROM model_versions 
WHERE run_id IN (SELECT run_uuid FROM runs WHERE experiment_id = 3);

-- 4. Delete Run Metadata (Metrics, Params, Tags)
DELETE FROM tags WHERE run_uuid IN (SELECT run_uuid FROM runs WHERE experiment_id = 3);
DELETE FROM metrics WHERE run_uuid IN (SELECT run_uuid FROM runs WHERE experiment_id = 3);
DELETE FROM params WHERE run_uuid IN (SELECT run_uuid FROM runs WHERE experiment_id = 3);
DELETE FROM latest_metrics WHERE run_uuid IN (SELECT run_uuid FROM runs WHERE experiment_id = 3);

-- 5. Delete the Runs themselves
DELETE FROM runs WHERE experiment_id = 3;

-- 6. Finally, Delete the Experiment
DELETE FROM experiments WHERE experiment_id = 3;