-- Initial schema: BTC candles table
CREATE TABLE IF NOT EXISTS btc_usd (
	time TIMESTAMP WITHOUT TIME ZONE PRIMARY KEY,
	low NUMERIC(31, 5),
	high NUMERIC(31, 5),
	open NUMERIC(31, 5),
	close NUMERIC(31, 5),
	volume NUMERIC(31, 5)
);
