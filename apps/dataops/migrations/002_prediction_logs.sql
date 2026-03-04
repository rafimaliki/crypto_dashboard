-- Add prediction logs table for ML model tracking
CREATE TABLE IF NOT EXISTS prediction_logs (
	id SERIAL PRIMARY KEY,
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
	candle_time TIMESTAMP WITHOUT TIME ZONE NOT NULL,
	model_identifier VARCHAR(255) NOT NULL,
	predicted_label INTEGER NOT NULL,
	actual_label INTEGER,
	close_price NUMERIC(31, 5),
	volume NUMERIC(31, 5),
	sma_12 NUMERIC(31, 5),
	volatility NUMERIC(31, 5),
	CONSTRAINT fk_candle_time FOREIGN KEY (candle_time) REFERENCES btc_usd(time) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_prediction_logs_model ON prediction_logs(model_identifier);
CREATE INDEX IF NOT EXISTS idx_prediction_logs_candle_time ON prediction_logs(candle_time);
CREATE INDEX IF NOT EXISTS idx_prediction_logs_actual_label_null ON prediction_logs(actual_label) WHERE actual_label IS NULL;
