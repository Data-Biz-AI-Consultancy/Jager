-- s_euro_stat
CREATE TABLE IF NOT EXISTS s_euro_stat.regional_gdp (
	id SERIAL PRIMARY KEY,
	geo_code VARCHAR(50) NOT NULL,
	geo_name VARCHAR(255),
	year INTEGER NOT NULL,
	gdp_value NUMERIC,
	unit VARCHAR(50),
	created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
	UNIQUE (geo_code, year, unit)
);

CREATE TABLE IF NOT EXISTS s_euro_stat.regional_crime_rates (
	id SERIAL PRIMARY KEY,
	geo_code VARCHAR(50) NOT NULL,
	geo_name VARCHAR(255),
	year INTEGER NOT NULL,
	offence_category VARCHAR(255),
	crime_count NUMERIC,
	unit VARCHAR(50),
	created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
	UNIQUE (geo_code, year, offence_category, unit)
);

CREATE TABLE IF NOT EXISTS s_euro_stat.inflation (
	id SERIAL PRIMARY KEY,
	geo_code VARCHAR(50) NOT NULL,
	geo_name VARCHAR(255),
	time VARCHAR(50) NOT NULL,
	coicop_code VARCHAR(50) NOT NULL,
	coicop_name VARCHAR(255),
	unit VARCHAR(50),
	value NUMERIC,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
	UNIQUE (geo_code, time, coicop_code, unit)
);

CREATE TABLE IF NOT EXISTS s_euro_stat.quarterly_gdp (
	id SERIAL PRIMARY KEY,
	geo_code VARCHAR(50) NOT NULL,
	geo_name VARCHAR(255),
	time VARCHAR(50) NOT NULL,
	na_item VARCHAR(50) NOT NULL,
	unit VARCHAR(50),
	s_adj VARCHAR(50),
	value NUMERIC,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
	UNIQUE (geo_code, time, na_item, unit, s_adj)
);

CREATE TABLE IF NOT EXISTS s_euro_stat.unemployment (
	id SERIAL PRIMARY KEY,
	geo_code VARCHAR(50) NOT NULL,
	geo_name VARCHAR(255),
	time VARCHAR(50) NOT NULL,
	age VARCHAR(50),
	sex VARCHAR(10),
	unit VARCHAR(50),
	s_adj VARCHAR(50),
	value NUMERIC,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
	UNIQUE (geo_code, time, age, sex, unit, s_adj)
);

CREATE TABLE IF NOT EXISTS s_euro_stat.house_price_index (
	id SERIAL PRIMARY KEY,
	geo_code VARCHAR(50) NOT NULL,
	geo_name VARCHAR(255),
	time VARCHAR(50) NOT NULL,
	purchase VARCHAR(50),
	unit VARCHAR(50),
	value NUMERIC,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
	UNIQUE (geo_code, time, purchase, unit)
);

CREATE TABLE IF NOT EXISTS s_euro_stat.fx_rates (
	id SERIAL PRIMARY KEY,
	base_currency VARCHAR(3) NOT NULL,
	target_currency VARCHAR(3) NOT NULL,
	rate NUMERIC NOT NULL,
	rate_date DATE NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
	UNIQUE (base_currency, target_currency, rate_date)
);

-- s_yahoo_finance
CREATE TABLE IF NOT EXISTS s_yahoo_finance.stock_prices (
	id SERIAL PRIMARY KEY,
	symbol VARCHAR(50) NOT NULL,
	price_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
	open_price NUMERIC,
	high_price NUMERIC,
	low_price NUMERIC,
	close_price NUMERIC,
	volume NUMERIC,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
	UNIQUE (symbol, price_timestamp)
);

-- prediction
CREATE TABLE IF NOT EXISTS prediction.stock_predictions (
	id SERIAL PRIMARY KEY,
	symbol VARCHAR(50) NOT NULL,
	prediction_date DATE NOT NULL,
	predicted_close_price NUMERIC NOT NULL,
	actual_close_price NUMERIC,
	trend VARCHAR(10),
	confidence NUMERIC,
	reasoning TEXT,
	model_name VARCHAR(100) NOT NULL,
	features JSONB,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
	UNIQUE (symbol, prediction_date, model_name)
);

-- training
CREATE TABLE IF NOT EXISTS training.trained_models (
	id SERIAL PRIMARY KEY,
	symbol VARCHAR(50) NOT NULL,
	model_name VARCHAR(100) NOT NULL,
	model_data BYTEA NOT NULL,
	r2_score NUMERIC,
	trained_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
	UNIQUE (symbol, model_name)
);
