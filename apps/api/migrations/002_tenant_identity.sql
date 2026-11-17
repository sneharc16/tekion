-- Applied transactionally by store.migrate; preserves all aggregate data.
CREATE TABLE records_v2 (kind VARCHAR(40) NOT NULL, id VARCHAR(100) NOT NULL, dealer VARCHAR(40) NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(kind,id,dealer));
INSERT INTO records_v2 SELECT kind,id,dealer,payload FROM records;
DROP TABLE records;
ALTER TABLE records_v2 RENAME TO records;
INSERT INTO schema_migrations(version) VALUES (2);
