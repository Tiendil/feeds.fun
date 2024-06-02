ALTER TABLE all_auth_recipe_users
  ADD COLUMN primary_or_recipe_user_id CHAR(36) NOT NULL DEFAULT ('0');

ALTER TABLE all_auth_recipe_users
  ADD COLUMN is_linked_or_is_a_primary_user BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE all_auth_recipe_users
  ADD COLUMN primary_or_recipe_user_time_joined BIGINT NOT NULL DEFAULT 0;

UPDATE all_auth_recipe_users
  SET primary_or_recipe_user_id = user_id
  WHERE primary_or_recipe_user_id = '0';

UPDATE all_auth_recipe_users
  SET primary_or_recipe_user_time_joined = time_joined
  WHERE primary_or_recipe_user_time_joined = 0;

ALTER TABLE all_auth_recipe_users
  ADD CONSTRAINT all_auth_recipe_users_primary_or_recipe_user_id_fkey
    FOREIGN KEY (app_id, primary_or_recipe_user_id)
    REFERENCES app_id_to_user_id (app_id, user_id) ON DELETE CASCADE;

ALTER TABLE all_auth_recipe_users
  ALTER primary_or_recipe_user_id DROP DEFAULT;

ALTER TABLE app_id_to_user_id
  ADD COLUMN primary_or_recipe_user_id CHAR(36) NOT NULL DEFAULT ('0');

ALTER TABLE app_id_to_user_id
  ADD COLUMN is_linked_or_is_a_primary_user BOOLEAN NOT NULL DEFAULT FALSE;

UPDATE app_id_to_user_id
  SET primary_or_recipe_user_id = user_id
  WHERE primary_or_recipe_user_id = '0';

ALTER TABLE app_id_to_user_id
  ADD CONSTRAINT app_id_to_user_id_primary_or_recipe_user_id_fkey
    FOREIGN KEY (app_id, primary_or_recipe_user_id)
    REFERENCES app_id_to_user_id (app_id, user_id) ON DELETE CASCADE;

ALTER TABLE app_id_to_user_id
    ALTER primary_or_recipe_user_id DROP DEFAULT;

DROP INDEX all_auth_recipe_users_pagination_index;

CREATE INDEX all_auth_recipe_users_pagination_index1 ON all_auth_recipe_users (
  app_id, tenant_id, primary_or_recipe_user_time_joined DESC, primary_or_recipe_user_id DESC);

CREATE INDEX all_auth_recipe_users_pagination_index2 ON all_auth_recipe_users (
  app_id, tenant_id, primary_or_recipe_user_time_joined ASC, primary_or_recipe_user_id DESC);

CREATE INDEX all_auth_recipe_users_pagination_index3 ON all_auth_recipe_users (
  recipe_id, app_id, tenant_id, primary_or_recipe_user_time_joined DESC, primary_or_recipe_user_id DESC);

CREATE INDEX all_auth_recipe_users_pagination_index4 ON all_auth_recipe_users (
  recipe_id, app_id, tenant_id, primary_or_recipe_user_time_joined ASC, primary_or_recipe_user_id DESC);

CREATE INDEX all_auth_recipe_users_primary_user_id_index ON all_auth_recipe_users (primary_or_recipe_user_id, app_id);

CREATE INDEX all_auth_recipe_users_recipe_id_index ON all_auth_recipe_users (app_id, recipe_id, tenant_id);

ALTER TABLE emailpassword_pswd_reset_tokens DROP CONSTRAINT IF EXISTS emailpassword_pswd_reset_tokens_user_id_fkey;

ALTER TABLE emailpassword_pswd_reset_tokens ADD CONSTRAINT emailpassword_pswd_reset_tokens_user_id_fkey FOREIGN KEY (app_id, user_id) REFERENCES app_id_to_user_id (app_id, user_id) ON DELETE CASCADE;

ALTER TABLE emailpassword_pswd_reset_tokens ADD COLUMN email VARCHAR(256);
