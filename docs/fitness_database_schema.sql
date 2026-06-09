-- Database Schema Export
-- Generated on: 2026-02-23 15:56:20
-- Fitness App Database Structure

-- Table: admin_refresh_tokens

CREATE TABLE admin_refresh_tokens (
	id SERIAL NOT NULL, 
	admin_id INTEGER NOT NULL, 
	token_hash VARCHAR(255) NOT NULL, 
	jti VARCHAR(255) NOT NULL, 
	expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	is_revoked BOOLEAN DEFAULT false, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
	last_used_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
	CONSTRAINT admin_refresh_tokens_pkey PRIMARY KEY (id), 
	CONSTRAINT fk_admin FOREIGN KEY(admin_id) REFERENCES admins (id) ON DELETE CASCADE, 
	CONSTRAINT admin_refresh_tokens_jti_key UNIQUE NULLS DISTINCT (jti)
)

;
CREATE INDEX UNIQUE admin_refresh_tokens_jti_key ON admin_refresh_tokens (jti);

-- Table: admins

CREATE TABLE admins (
	id SERIAL NOT NULL, 
	username VARCHAR(255) NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	is_active BOOLEAN DEFAULT true, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
	CONSTRAINT admins_pkey PRIMARY KEY (id), 
	CONSTRAINT admins_email_key UNIQUE NULLS DISTINCT (email), 
	CONSTRAINT admins_username_key UNIQUE NULLS DISTINCT (username)
)

;
CREATE INDEX UNIQUE admins_email_key ON admins (email);
CREATE INDEX UNIQUE admins_username_key ON admins (username);

-- Table: bmi_classification

CREATE TABLE bmi_classification (
	id SERIAL NOT NULL, 
	category_name VARCHAR NOT NULL, 
	min_bmi DOUBLE PRECISION, 
	max_bmi DOUBLE PRECISION, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
	CONSTRAINT bmi_classification_pkey PRIMARY KEY (id)
)

;

-- Table: daily_activities

CREATE TABLE daily_activities (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	date DATE NOT NULL, 
	steps INTEGER DEFAULT 0, 
	distance_km DOUBLE PRECISION DEFAULT 0.0, 
	calories DOUBLE PRECISION DEFAULT 0.0, 
	active_minutes DOUBLE PRECISION DEFAULT 0.0, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
	CONSTRAINT daily_activities_pkey PRIMARY KEY (id), 
	CONSTRAINT fk_daily_activities_user FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	CONSTRAINT unique_user_date UNIQUE NULLS DISTINCT (user_id, date)
)

;
CREATE INDEX UNIQUE unique_user_date ON daily_activities (user_id, date);

-- Table: meals

CREATE TABLE meals (
	id SERIAL NOT NULL, 
	bmi_category_id INTEGER NOT NULL, 
	meal_type VARCHAR NOT NULL, 
	food_item VARCHAR NOT NULL, 
	calories INTEGER NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
	CONSTRAINT meals_pkey PRIMARY KEY (id), 
	CONSTRAINT fk_meals_bmi_category FOREIGN KEY(bmi_category_id) REFERENCES bmi_classification (id) ON DELETE CASCADE
)

;

-- Table: refresh_tokens

CREATE TABLE refresh_tokens (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	token_hash VARCHAR NOT NULL, 
	expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	last_used_at TIMESTAMP WITHOUT TIME ZONE, 
	is_revoked BOOLEAN, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	jti VARCHAR(255) NOT NULL, 
	CONSTRAINT refresh_tokens_pkey PRIMARY KEY (id), 
	CONSTRAINT refresh_tokens_user_id_fkey FOREIGN KEY(user_id) REFERENCES users (id), 
	CONSTRAINT refresh_tokens_jti_key UNIQUE NULLS DISTINCT (jti)
)

;
CREATE INDEX idx_refresh_tokens_jti ON refresh_tokens (jti);
CREATE INDEX ix_refresh_tokens_id ON refresh_tokens (id);
CREATE INDEX ix_refresh_tokens_user_id ON refresh_tokens (user_id);
CREATE INDEX UNIQUE refresh_tokens_jti_key ON refresh_tokens (jti);

-- Table: user_monthly_activity

CREATE TABLE user_monthly_activity (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	year INTEGER NOT NULL, 
	month INTEGER NOT NULL, 
	total_steps INTEGER DEFAULT 0, 
	total_distance_km DOUBLE PRECISION DEFAULT 0.0, 
	total_calories DOUBLE PRECISION DEFAULT 0.0, 
	total_active_minutes DOUBLE PRECISION DEFAULT 0.0, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
	CONSTRAINT user_monthly_activity_pkey PRIMARY KEY (id), 
	CONSTRAINT fk_user_monthly_activity_user FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	CONSTRAINT unique_user_year_month UNIQUE NULLS DISTINCT (user_id, year, month)
)

;
CREATE INDEX UNIQUE unique_user_year_month ON user_monthly_activity (user_id, year, month);

-- Table: user_yearly_activity

CREATE TABLE user_yearly_activity (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	year INTEGER NOT NULL, 
	total_steps INTEGER DEFAULT 0, 
	total_distance_km DOUBLE PRECISION DEFAULT 0.0, 
	total_calories DOUBLE PRECISION DEFAULT 0.0, 
	total_active_minutes DOUBLE PRECISION DEFAULT 0.0, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
	CONSTRAINT user_yearly_activity_pkey PRIMARY KEY (id), 
	CONSTRAINT fk_user_yearly_activity_user FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	CONSTRAINT unique_user_year UNIQUE NULLS DISTINCT (user_id, year)
)

;
CREATE INDEX UNIQUE unique_user_year ON user_yearly_activity (user_id, year);

-- Table: users

CREATE TABLE users (
	id SERIAL NOT NULL, 
	email VARCHAR NOT NULL, 
	password VARCHAR NOT NULL, 
	otp VARCHAR, 
	otp_created_at TIMESTAMP WITHOUT TIME ZONE, 
	is_verified BOOLEAN, 
	username VARCHAR(100) NOT NULL, 
	gender VARCHAR(20), 
	age INTEGER, 
	weight DOUBLE PRECISION, 
	height DOUBLE PRECISION, 
	bmi DOUBLE PRECISION, 
	weight_goal DOUBLE PRECISION, 
	activity_level VARCHAR(50), 
	profile_image VARCHAR(255), 
	CONSTRAINT users_pkey PRIMARY KEY (id)
)

;
CREATE INDEX UNIQUE ix_users_email ON users (email);
CREATE INDEX ix_users_id ON users (id);

-- Table: workouts

CREATE TABLE workouts (
	id SERIAL NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	description TEXT NOT NULL, 
	workout_image_url TEXT NOT NULL, 
	workout_video_url TEXT NOT NULL, 
	duration INTEGER NOT NULL, 
	calorie_burn INTEGER NOT NULL, 
	activity_level VARCHAR(50) NOT NULL, 
	workout_category VARCHAR(50) NOT NULL, 
	workout_type VARCHAR(50) NOT NULL DEFAULT 'home', 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
	CONSTRAINT workouts_pkey PRIMARY KEY (id)
)

;
