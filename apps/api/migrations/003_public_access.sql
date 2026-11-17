CREATE TABLE IF NOT EXISTS public_tokens (token VARCHAR(100) PRIMARY KEY, dealer VARCHAR(40) NOT NULL, report_id VARCHAR(100) NOT NULL);
CREATE TABLE IF NOT EXISTS rate_limits (client VARCHAR(100) NOT NULL, "window" BIGINT NOT NULL, count INTEGER NOT NULL, PRIMARY KEY(client,"window"));
-- store.migrate backfills tokens from existing report snapshots; version 3 recorded there.
