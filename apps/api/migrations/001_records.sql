-- Applied by app.store.migrate; JSON aggregate store with scoped composite identities.
CREATE TABLE IF NOT EXISTS records (kind VARCHAR(40) NOT NULL, id VARCHAR(100) NOT NULL, dealer VARCHAR(40) NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(kind,id));
CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY);
