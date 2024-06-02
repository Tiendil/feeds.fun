-- General Tables

CREATE TABLE IF NOT EXISTS apps  (
  app_id VARCHAR(64) NOT NULL DEFAULT 'public',
  created_at_time BIGINT,
  CONSTRAINT apps_pkey PRIMARY KEY(app_id)
);

INSERT INTO apps (app_id, created_at_time)
  VALUES ('public', 0) ON CONFLICT DO NOTHING;

------------------------------------------------------------

CREATE TABLE IF NOT EXISTS tenants (
  app_id VARCHAR(64) NOT NULL DEFAULT 'public',
  tenant_id VARCHAR(64) NOT NULL DEFAULT 'public',
  created_at_time BIGINT ,
  CONSTRAINT tenants_pkey
    PRIMARY KEY (app_id, tenant_id),
  CONSTRAINT tenants_app_id_fkey FOREIGN KEY(app_id)
    REFERENCES apps (app_id) ON DELETE CASCADE
);

INSERT INTO tenants (app_id, tenant_id, created_at_time)
  VALUES ('public', 'public', 0) ON CONFLICT DO NOTHING;

CREATE INDEX IF NOT EXISTS tenants_app_id_index ON tenants (app_id);

------------------------------------------------------------

ALTER TABLE key_value
  ADD COLUMN IF NOT EXISTS app_id VARCHAR(64) DEFAULT 'public',
  ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(64) DEFAULT 'public';

ALTER TABLE key_value
  DROP CONSTRAINT key_value_pkey;

ALTER TABLE key_value
  ADD CONSTRAINT key_value_pkey
    PRIMARY KEY (app_id, tenant_id, name);

ALTER TABLE key_value
  DROP CONSTRAINT IF EXISTS key_value_tenant_id_fkey;

ALTER TABLE key_value
  ADD CONSTRAINT key_value_tenant_id_fkey
    FOREIGN KEY (app_id, tenant_id)
    REFERENCES tenants (app_id, tenant_id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS key_value_tenant_id_index ON key_value (app_id, tenant_id);

------------------------------------------------------------

CREATE TABLE IF NOT EXISTS app_id_to_user_id (
  app_id VARCHAR(64) NOT NULL DEFAULT 'public',
  user_id CHAR(36) NOT NULL,
  recipe_id VARCHAR(128) NOT NULL,
  CONSTRAINT app_id_to_user_id_pkey
    PRIMARY KEY (app_id, user_id),
  CONSTRAINT app_id_to_user_id_app_id_fkey
    FOREIGN KEY(app_id) REFERENCES apps (app_id) ON DELETE CASCADE
);

INSERT INTO app_id_to_user_id (user_id, recipe_id)
  SELECT user_id, recipe_id
  FROM all_auth_recipe_users ON CONFLICT DO NOTHING;

CREATE INDEX IF NOT EXISTS app_id_to_user_id_app_id_index ON app_id_to_user_id (app_id);

------------------------------------------------------------

ALTER TABLE all_auth_recipe_users
  ADD COLUMN IF NOT EXISTS app_id VARCHAR(64) DEFAULT 'public',
  ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(64) DEFAULT 'public';

ALTER TABLE all_auth_recipe_users
  DROP CONSTRAINT all_auth_recipe_users_pkey CASCADE;

ALTER TABLE all_auth_recipe_users
  ADD CONSTRAINT all_auth_recipe_users_pkey
    PRIMARY KEY (app_id, tenant_id, user_id);

ALTER TABLE all_auth_recipe_users
  DROP CONSTRAINT IF EXISTS all_auth_recipe_users_tenant_id_fkey;

ALTER TABLE all_auth_recipe_users
  ADD CONSTRAINT all_auth_recipe_users_tenant_id_fkey
    FOREIGN KEY (app_id, tenant_id)
    REFERENCES tenants (app_id, tenant_id) ON DELETE CASCADE;

ALTER TABLE all_auth_recipe_users
  DROP CONSTRAINT IF EXISTS all_auth_recipe_users_user_id_fkey;

ALTER TABLE all_auth_recipe_users
  ADD CONSTRAINT all_auth_recipe_users_user_id_fkey
    FOREIGN KEY (app_id, user_id)
    REFERENCES app_id_to_user_id (app_id, user_id) ON DELETE CASCADE;

DROP INDEX all_auth_recipe_users_pagination_index;

CREATE INDEX all_auth_recipe_users_pagination_index ON all_auth_recipe_users (time_joined DESC, user_id DESC, tenant_id DESC, app_id DESC);

CREATE INDEX IF NOT EXISTS all_auth_recipe_user_id_index ON all_auth_recipe_users (app_id, user_id);

CREATE INDEX IF NOT EXISTS all_auth_recipe_tenant_id_index ON all_auth_recipe_users (app_id, tenant_id);

-- Multitenancy

CREATE TABLE IF NOT EXISTS tenant_configs (
  connection_uri_domain VARCHAR(256) DEFAULT '',
  app_id VARCHAR(64) DEFAULT 'public',
  tenant_id VARCHAR(64) DEFAULT 'public',
  core_config TEXT,
  email_password_enabled BOOLEAN,
  passwordless_enabled BOOLEAN,
  third_party_enabled BOOLEAN,
  CONSTRAINT tenant_configs_pkey
    PRIMARY KEY (connection_uri_domain, app_id, tenant_id)
);

------------------------------------------------------------

CREATE TABLE IF NOT EXISTS tenant_thirdparty_providers (
  connection_uri_domain VARCHAR(256) DEFAULT '',
  app_id VARCHAR(64) DEFAULT 'public',
  tenant_id VARCHAR(64) DEFAULT 'public',
  third_party_id VARCHAR(28) NOT NULL,
  name VARCHAR(64),
  authorization_endpoint TEXT,
  authorization_endpoint_query_params TEXT,
  token_endpoint TEXT,
  token_endpoint_body_params TEXT,
  user_info_endpoint TEXT,
  user_info_endpoint_query_params TEXT,
  user_info_endpoint_headers TEXT,
  jwks_uri TEXT,
  oidc_discovery_endpoint TEXT,
  require_email BOOLEAN,
  user_info_map_from_id_token_payload_user_id VARCHAR(64),
  user_info_map_from_id_token_payload_email VARCHAR(64),
  user_info_map_from_id_token_payload_email_verified VARCHAR(64),
  user_info_map_from_user_info_endpoint_user_id VARCHAR(64),
  user_info_map_from_user_info_endpoint_email VARCHAR(64),
  user_info_map_from_user_info_endpoint_email_verified VARCHAR(64),
  CONSTRAINT tenant_thirdparty_providers_pkey
    PRIMARY KEY (connection_uri_domain, app_id, tenant_id, third_party_id),
  CONSTRAINT tenant_thirdparty_providers_tenant_id_fkey
    FOREIGN KEY(connection_uri_domain, app_id, tenant_id)
    REFERENCES tenant_configs (connection_uri_domain, app_id, tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS tenant_thirdparty_providers_tenant_id_index ON tenant_thirdparty_providers (connection_uri_domain, app_id, tenant_id);

------------------------------------------------------------

CREATE TABLE IF NOT EXISTS tenant_thirdparty_provider_clients (
  connection_uri_domain VARCHAR(256) DEFAULT '',
  app_id VARCHAR(64) DEFAULT 'public',
  tenant_id VARCHAR(64) DEFAULT 'public',
  third_party_id VARCHAR(28) NOT NULL,
  client_type VARCHAR(64) NOT NULL DEFAULT '',
  client_id VARCHAR(256) NOT NULL,
  client_secret TEXT,
  scope VARCHAR(128)[],
  force_pkce BOOLEAN,
  additional_config TEXT,
  CONSTRAINT tenant_thirdparty_provider_clients_pkey
    PRIMARY KEY (connection_uri_domain, app_id, tenant_id, third_party_id, client_type),
  CONSTRAINT tenant_thirdparty_provider_clients_third_party_id_fkey
    FOREIGN KEY (connection_uri_domain, app_id, tenant_id, third_party_id)
    REFERENCES tenant_thirdparty_providers (connection_uri_domain, app_id, tenant_id, third_party_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS tenant_thirdparty_provider_clients_third_party_id_index ON tenant_thirdparty_provider_clients (connection_uri_domain, app_id, tenant_id, third_party_id);

-- Session

ALTER TABLE session_info
  ADD COLUMN IF NOT EXISTS app_id VARCHAR(64) DEFAULT 'public',
  ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(64) DEFAULT 'public';

ALTER TABLE session_info
  DROP CONSTRAINT session_info_pkey CASCADE;

ALTER TABLE session_info
  ADD CONSTRAINT session_info_pkey
    PRIMARY KEY (app_id, tenant_id, session_handle);

ALTER TABLE session_info
  DROP CONSTRAINT IF EXISTS session_info_tenant_id_fkey;

ALTER TABLE session_info
  ADD CONSTRAINT session_info_tenant_id_fkey
    FOREIGN KEY (app_id, tenant_id)
    REFERENCES tenants (app_id, tenant_id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS session_expiry_index ON session_info (expires_at);

CREATE INDEX IF NOT EXISTS session_info_tenant_id_index ON session_info (app_id, tenant_id);

------------------------------------------------------------

ALTER TABLE session_access_token_signing_keys
  ADD COLUMN IF NOT EXISTS app_id VARCHAR(64) DEFAULT 'public';

ALTER TABLE session_access_token_signing_keys
  DROP CONSTRAINT session_access_token_signing_keys_pkey CASCADE;

ALTER TABLE session_access_token_signing_keys
  ADD CONSTRAINT session_access_token_signing_keys_pkey
    PRIMARY KEY (app_id, created_at_time);

ALTER TABLE session_access_token_signing_keys
  DROP CONSTRAINT IF EXISTS session_access_token_signing_keys_app_id_fkey;

ALTER TABLE session_access_token_signing_keys
  ADD CONSTRAINT session_access_token_signing_keys_app_id_fkey
    FOREIGN KEY (app_id)
    REFERENCES apps (app_id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS access_token_signing_keys_app_id_index ON session_access_token_signing_keys (app_id);

-- JWT

ALTER TABLE jwt_signing_keys
  ADD COLUMN IF NOT EXISTS app_id VARCHAR(64) DEFAULT 'public';

ALTER TABLE jwt_signing_keys
  DROP CONSTRAINT jwt_signing_keys_pkey CASCADE;

ALTER TABLE jwt_signing_keys
  ADD CONSTRAINT jwt_signing_keys_pkey
    PRIMARY KEY (app_id, key_id);

ALTER TABLE jwt_signing_keys
  DROP CONSTRAINT IF EXISTS jwt_signing_keys_app_id_fkey;

ALTER TABLE jwt_signing_keys
  ADD CONSTRAINT jwt_signing_keys_app_id_fkey
    FOREIGN KEY (app_id)
    REFERENCES apps (app_id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS jwt_signing_keys_app_id_index ON jwt_signing_keys (app_id);

-- EmailVerification

ALTER TABLE emailverification_verified_emails
  ADD COLUMN IF NOT EXISTS app_id VARCHAR(64) DEFAULT 'public';

ALTER TABLE emailverification_verified_emails
  DROP CONSTRAINT emailverification_verified_emails_pkey CASCADE;

ALTER TABLE emailverification_verified_emails
  ADD CONSTRAINT emailverification_verified_emails_pkey
    PRIMARY KEY (app_id, user_id, email);

ALTER TABLE emailverification_verified_emails
  DROP CONSTRAINT IF EXISTS emailverification_verified_emails_app_id_fkey;

ALTER TABLE emailverification_verified_emails
  ADD CONSTRAINT emailverification_verified_emails_app_id_fkey
    FOREIGN KEY (app_id)
    REFERENCES apps (app_id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS emailverification_verified_emails_app_id_index ON emailverification_verified_emails (app_id);

------------------------------------------------------------

ALTER TABLE emailverification_tokens
  ADD COLUMN IF NOT EXISTS app_id VARCHAR(64) DEFAULT 'public',
  ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(64) DEFAULT 'public';

ALTER TABLE emailverification_tokens
  DROP CONSTRAINT emailverification_tokens_pkey CASCADE;

ALTER TABLE emailverification_tokens
  ADD CONSTRAINT emailverification_tokens_pkey
    PRIMARY KEY (app_id, tenant_id, user_id, email, token);

ALTER TABLE emailverification_tokens
  DROP CONSTRAINT IF EXISTS emailverification_tokens_tenant_id_fkey;

ALTER TABLE emailverification_tokens
  ADD CONSTRAINT emailverification_tokens_tenant_id_fkey
    FOREIGN KEY (app_id, tenant_id)
    REFERENCES tenants (app_id, tenant_id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS emailverification_tokens_tenant_id_index ON emailverification_tokens (app_id, tenant_id);

-- EmailPassword

ALTER TABLE emailpassword_users
  ADD COLUMN IF NOT EXISTS app_id VARCHAR(64) DEFAULT 'public';

ALTER TABLE emailpassword_users
  DROP CONSTRAINT emailpassword_users_pkey CASCADE;

ALTER TABLE emailpassword_users
  DROP CONSTRAINT IF EXISTS emailpassword_users_email_key CASCADE;

ALTER TABLE emailpassword_users
  ADD CONSTRAINT emailpassword_users_pkey
    PRIMARY KEY (app_id, user_id);

ALTER TABLE emailpassword_users
  DROP CONSTRAINT IF EXISTS emailpassword_users_user_id_fkey;

ALTER TABLE emailpassword_users
  ADD CONSTRAINT emailpassword_users_user_id_fkey
    FOREIGN KEY (app_id, user_id)
    REFERENCES app_id_to_user_id (app_id, user_id) ON DELETE CASCADE;

------------------------------------------------------------

CREATE TABLE IF NOT EXISTS emailpassword_user_to_tenant (
  app_id VARCHAR(64) DEFAULT 'public',
  tenant_id VARCHAR(64) DEFAULT 'public',
  user_id CHAR(36) NOT NULL,
  email VARCHAR(256) NOT NULL,
  CONSTRAINT emailpassword_user_to_tenant_email_key
    UNIQUE (app_id, tenant_id, email),
  CONSTRAINT emailpassword_user_to_tenant_pkey
    PRIMARY KEY (app_id, tenant_id, user_id),
  CONSTRAINT emailpassword_user_to_tenant_user_id_fkey
    FOREIGN KEY (app_id, tenant_id, user_id)
    REFERENCES all_auth_recipe_users (app_id, tenant_id, user_id) ON DELETE CASCADE
);

ALTER TABLE emailpassword_user_to_tenant
  DROP CONSTRAINT IF EXISTS emailpassword_user_to_tenant_email_key;

ALTER TABLE emailpassword_user_to_tenant
  ADD CONSTRAINT emailpassword_user_to_tenant_email_key
    UNIQUE (app_id, tenant_id, email);

ALTER TABLE emailpassword_user_to_tenant
  DROP CONSTRAINT IF EXISTS emailpassword_user_to_tenant_user_id_fkey;

ALTER TABLE emailpassword_user_to_tenant
  ADD CONSTRAINT emailpassword_user_to_tenant_user_id_fkey
    FOREIGN KEY (app_id, tenant_id, user_id)
    REFERENCES all_auth_recipe_users (app_id, tenant_id, user_id) ON DELETE CASCADE;

INSERT INTO emailpassword_user_to_tenant (user_id, email)
  SELECT user_id, email FROM emailpassword_users ON CONFLICT DO NOTHING;

------------------------------------------------------------

ALTER TABLE emailpassword_pswd_reset_tokens
  ADD COLUMN IF NOT EXISTS app_id VARCHAR(64) DEFAULT 'public';

ALTER TABLE emailpassword_pswd_reset_tokens
  DROP CONSTRAINT emailpassword_pswd_reset_tokens_pkey CASCADE;

ALTER TABLE emailpassword_pswd_reset_tokens
  ADD CONSTRAINT emailpassword_pswd_reset_tokens_pkey
    PRIMARY KEY (app_id, user_id, token);

ALTER TABLE emailpassword_pswd_reset_tokens
  DROP CONSTRAINT IF EXISTS emailpassword_pswd_reset_tokens_user_id_fkey;

ALTER TABLE emailpassword_pswd_reset_tokens
  ADD CONSTRAINT emailpassword_pswd_reset_tokens_user_id_fkey
    FOREIGN KEY (app_id, user_id)
    REFERENCES emailpassword_users (app_id, user_id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS emailpassword_pswd_reset_tokens_user_id_index ON emailpassword_pswd_reset_tokens (app_id, user_id);

-- Passwordless

ALTER TABLE passwordless_users
  ADD COLUMN IF NOT EXISTS app_id VARCHAR(64) DEFAULT 'public';

ALTER TABLE passwordless_users
  DROP CONSTRAINT passwordless_users_pkey CASCADE;

ALTER TABLE passwordless_users
  ADD CONSTRAINT passwordless_users_pkey
    PRIMARY KEY (app_id, user_id);

ALTER TABLE passwordless_users
  DROP CONSTRAINT IF EXISTS passwordless_users_email_key;

ALTER TABLE passwordless_users
  DROP CONSTRAINT IF EXISTS passwordless_users_phone_number_key;

ALTER TABLE passwordless_users
  DROP CONSTRAINT IF EXISTS passwordless_users_user_id_fkey;

ALTER TABLE passwordless_users
  ADD CONSTRAINT passwordless_users_user_id_fkey
    FOREIGN KEY (app_id, user_id)
    REFERENCES app_id_to_user_id (app_id, user_id) ON DELETE CASCADE;

------------------------------------------------------------

CREATE TABLE IF NOT EXISTS passwordless_user_to_tenant (
  app_id VARCHAR(64) DEFAULT 'public',
  tenant_id VARCHAR(64) DEFAULT 'public',
  user_id CHAR(36) NOT NULL,
  email VARCHAR(256),
  phone_number VARCHAR(256),
  CONSTRAINT passwordless_user_to_tenant_email_key
    UNIQUE (app_id, tenant_id, email),
  CONSTRAINT passwordless_user_to_tenant_phone_number_key
    UNIQUE (app_id, tenant_id, phone_number),
  CONSTRAINT passwordless_user_to_tenant_pkey
    PRIMARY KEY (app_id, tenant_id, user_id),
  CONSTRAINT passwordless_user_to_tenant_user_id_fkey
    FOREIGN KEY (app_id, tenant_id, user_id)
    REFERENCES all_auth_recipe_users (app_id, tenant_id, user_id) ON DELETE CASCADE
);

ALTER TABLE passwordless_user_to_tenant
  DROP CONSTRAINT IF EXISTS passwordless_user_to_tenant_user_id_fkey;

ALTER TABLE passwordless_user_to_tenant
  ADD CONSTRAINT passwordless_user_to_tenant_user_id_fkey
    FOREIGN KEY (app_id, tenant_id, user_id)
    REFERENCES all_auth_recipe_users (app_id, tenant_id, user_id) ON DELETE CASCADE;

INSERT INTO passwordless_user_to_tenant (user_id, email, phone_number)
  SELECT user_id, email, phone_number FROM passwordless_users ON CONFLICT DO NOTHING;

------------------------------------------------------------

ALTER TABLE passwordless_devices
  ADD COLUMN IF NOT EXISTS app_id VARCHAR(64) DEFAULT 'public',
  ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(64) DEFAULT 'public';

ALTER TABLE passwordless_devices
  DROP CONSTRAINT passwordless_devices_pkey CASCADE;

ALTER TABLE passwordless_devices
  ADD CONSTRAINT passwordless_devices_pkey
    PRIMARY KEY (app_id, tenant_id, device_id_hash);

ALTER TABLE passwordless_devices
  DROP CONSTRAINT IF EXISTS passwordless_devices_tenant_id_fkey;

ALTER TABLE passwordless_devices
  ADD CONSTRAINT passwordless_devices_tenant_id_fkey
    FOREIGN KEY (app_id, tenant_id)
    REFERENCES tenants (app_id, tenant_id) ON DELETE CASCADE;

DROP INDEX IF EXISTS passwordless_devices_email_index;

CREATE INDEX IF NOT EXISTS passwordless_devices_email_index ON passwordless_devices (app_id, tenant_id, email);

DROP INDEX IF EXISTS passwordless_devices_phone_number_index;

CREATE INDEX IF NOT EXISTS passwordless_devices_phone_number_index ON passwordless_devices (app_id, tenant_id, phone_number);

CREATE INDEX IF NOT EXISTS passwordless_devices_tenant_id_index ON passwordless_devices (app_id, tenant_id);

------------------------------------------------------------

ALTER TABLE passwordless_codes
  ADD COLUMN IF NOT EXISTS app_id VARCHAR(64) DEFAULT 'public',
  ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(64) DEFAULT 'public';

ALTER TABLE passwordless_codes
  DROP CONSTRAINT passwordless_codes_pkey CASCADE;

ALTER TABLE passwordless_codes
  ADD CONSTRAINT passwordless_codes_pkey
    PRIMARY KEY (app_id, tenant_id, code_id);

ALTER TABLE passwordless_codes
  DROP CONSTRAINT IF EXISTS passwordless_codes_device_id_hash_fkey;

ALTER TABLE passwordless_codes
  ADD CONSTRAINT passwordless_codes_device_id_hash_fkey
    FOREIGN KEY (app_id, tenant_id, device_id_hash)
    REFERENCES passwordless_devices (app_id, tenant_id, device_id_hash) ON DELETE CASCADE;

ALTER TABLE passwordless_codes
  DROP CONSTRAINT passwordless_codes_link_code_hash_key;

ALTER TABLE passwordless_codes
  DROP CONSTRAINT IF EXISTS passwordless_codes_link_code_hash_key;

ALTER TABLE passwordless_codes
  ADD CONSTRAINT passwordless_codes_link_code_hash_key
    UNIQUE (app_id, tenant_id, link_code_hash);

DROP INDEX IF EXISTS passwordless_codes_created_at_index;

CREATE INDEX IF NOT EXISTS passwordless_codes_created_at_index ON passwordless_codes (app_id, tenant_id, created_at);

DROP INDEX IF EXISTS passwordless_codes_device_id_hash_index;
CREATE INDEX IF NOT EXISTS passwordless_codes_device_id_hash_index ON passwordless_codes (app_id, tenant_id, device_id_hash);

-- ThirdParty

ALTER TABLE thirdparty_users
  ADD COLUMN IF NOT EXISTS app_id VARCHAR(64) DEFAULT 'public';

ALTER TABLE thirdparty_users
  DROP CONSTRAINT thirdparty_users_pkey CASCADE;

ALTER TABLE thirdparty_users
  DROP CONSTRAINT IF EXISTS thirdparty_users_user_id_key CASCADE;

ALTER TABLE thirdparty_users
  ADD CONSTRAINT thirdparty_users_pkey
    PRIMARY KEY (app_id, user_id);

ALTER TABLE thirdparty_users
  DROP CONSTRAINT IF EXISTS thirdparty_users_user_id_fkey;

ALTER TABLE thirdparty_users
  ADD CONSTRAINT thirdparty_users_user_id_fkey
    FOREIGN KEY (app_id, user_id)
    REFERENCES app_id_to_user_id (app_id, user_id) ON DELETE CASCADE;

DROP INDEX IF EXISTS thirdparty_users_thirdparty_user_id_index;

CREATE INDEX IF NOT EXISTS thirdparty_users_thirdparty_user_id_index ON thirdparty_users (app_id, third_party_id, third_party_user_id);

DROP INDEX IF EXISTS thirdparty_users_email_index;

CREATE INDEX IF NOT EXISTS thirdparty_users_email_index ON thirdparty_users (app_id, email);

------------------------------------------------------------

CREATE TABLE IF NOT EXISTS thirdparty_user_to_tenant (
  app_id VARCHAR(64) DEFAULT 'public',
  tenant_id VARCHAR(64) DEFAULT 'public',
  user_id CHAR(36) NOT NULL,
  third_party_id VARCHAR(28) NOT NULL,
  third_party_user_id VARCHAR(256) NOT NULL,
  CONSTRAINT thirdparty_user_to_tenant_third_party_user_id_key
    UNIQUE (app_id, tenant_id, third_party_id, third_party_user_id),
  CONSTRAINT thirdparty_user_to_tenant_pkey
    PRIMARY KEY (app_id, tenant_id, user_id),
  CONSTRAINT thirdparty_user_to_tenant_user_id_fkey
    FOREIGN KEY (app_id, tenant_id, user_id)
    REFERENCES all_auth_recipe_users (app_id, tenant_id, user_id) ON DELETE CASCADE
);

ALTER TABLE thirdparty_user_to_tenant
  DROP CONSTRAINT IF EXISTS thirdparty_user_to_tenant_third_party_user_id_key;

ALTER TABLE thirdparty_user_to_tenant
  ADD CONSTRAINT thirdparty_user_to_tenant_third_party_user_id_key
    UNIQUE (app_id, tenant_id, third_party_id, third_party_user_id);

ALTER TABLE thirdparty_user_to_tenant
  DROP CONSTRAINT IF EXISTS thirdparty_user_to_tenant_user_id_fkey;

ALTER TABLE thirdparty_user_to_tenant
  ADD CONSTRAINT thirdparty_user_to_tenant_user_id_fkey
    FOREIGN KEY (app_id, tenant_id, user_id)
    REFERENCES all_auth_recipe_users (app_id, tenant_id, user_id) ON DELETE CASCADE;

INSERT INTO thirdparty_user_to_tenant (user_id, third_party_id, third_party_user_id)
  SELECT user_id, third_party_id, third_party_user_id FROM thirdparty_users ON CONFLICT DO NOTHING;

-- UserIdMapping

ALTER TABLE userid_mapping
  ADD COLUMN IF NOT EXISTS app_id VARCHAR(64) DEFAULT 'public';

ALTER TABLE userid_mapping
  DROP CONSTRAINT IF EXISTS userid_mapping_pkey CASCADE;

ALTER TABLE userid_mapping
  ADD CONSTRAINT userid_mapping_pkey
    PRIMARY KEY (app_id, supertokens_user_id, external_user_id);

ALTER TABLE userid_mapping
  DROP CONSTRAINT IF EXISTS userid_mapping_supertokens_user_id_key;

ALTER TABLE userid_mapping
  ADD CONSTRAINT userid_mapping_supertokens_user_id_key
    UNIQUE (app_id, supertokens_user_id);

ALTER TABLE userid_mapping
  DROP CONSTRAINT IF EXISTS userid_mapping_external_user_id_key;

ALTER TABLE userid_mapping
  ADD CONSTRAINT userid_mapping_external_user_id_key
    UNIQUE (app_id, external_user_id);

ALTER TABLE userid_mapping
  DROP CONSTRAINT IF EXISTS userid_mapping_supertokens_user_id_fkey;

ALTER TABLE userid_mapping
  ADD CONSTRAINT userid_mapping_supertokens_user_id_fkey
    FOREIGN KEY (app_id, supertokens_user_id)
    REFERENCES app_id_to_user_id (app_id, user_id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS userid_mapping_supertokens_user_id_index ON userid_mapping (app_id, supertokens_user_id);

-- UserRoles

ALTER TABLE roles
  ADD COLUMN IF NOT EXISTS app_id VARCHAR(64) DEFAULT 'public';

ALTER TABLE roles
  DROP CONSTRAINT roles_pkey CASCADE;

ALTER TABLE roles
  ADD CONSTRAINT roles_pkey
    PRIMARY KEY (app_id, role);

ALTER TABLE roles
  DROP CONSTRAINT IF EXISTS roles_app_id_fkey;

ALTER TABLE roles
  ADD CONSTRAINT roles_app_id_fkey
    FOREIGN KEY (app_id)
    REFERENCES apps (app_id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS roles_app_id_index ON roles (app_id);

------------------------------------------------------------

ALTER TABLE role_permissions
  ADD COLUMN IF NOT EXISTS app_id VARCHAR(64) DEFAULT 'public';

ALTER TABLE role_permissions
  DROP CONSTRAINT role_permissions_pkey CASCADE;

ALTER TABLE role_permissions
  ADD CONSTRAINT role_permissions_pkey
    PRIMARY KEY (app_id, role, permission);

ALTER TABLE role_permissions
  DROP CONSTRAINT IF EXISTS role_permissions_role_fkey;

ALTER TABLE role_permissions
  ADD CONSTRAINT role_permissions_role_fkey
    FOREIGN KEY (app_id, role)
    REFERENCES roles (app_id, role) ON DELETE CASCADE;

DROP INDEX IF EXISTS role_permissions_permission_index;

CREATE INDEX IF NOT EXISTS role_permissions_permission_index ON role_permissions (app_id, permission);

CREATE INDEX IF NOT EXISTS role_permissions_role_index ON role_permissions (app_id, role);

------------------------------------------------------------

ALTER TABLE user_roles
  ADD COLUMN IF NOT EXISTS app_id VARCHAR(64) DEFAULT 'public',
  ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(64) DEFAULT 'public';

ALTER TABLE user_roles
  DROP CONSTRAINT user_roles_pkey CASCADE;

ALTER TABLE user_roles
  ADD CONSTRAINT user_roles_pkey
    PRIMARY KEY (app_id, tenant_id, user_id, role);

ALTER TABLE user_roles
  DROP CONSTRAINT IF EXISTS user_roles_tenant_id_fkey;

ALTER TABLE user_roles
  ADD CONSTRAINT user_roles_tenant_id_fkey
    FOREIGN KEY (app_id, tenant_id)
    REFERENCES tenants (app_id, tenant_id) ON DELETE CASCADE;

ALTER TABLE user_roles
  DROP CONSTRAINT IF EXISTS user_roles_role_fkey;

ALTER TABLE user_roles
  ADD CONSTRAINT user_roles_role_fkey
    FOREIGN KEY (app_id, role)
    REFERENCES roles (app_id, role) ON DELETE CASCADE;

DROP INDEX IF EXISTS user_roles_role_index;

CREATE INDEX IF NOT EXISTS user_roles_role_index ON user_roles (app_id, tenant_id, role);

CREATE INDEX IF NOT EXISTS user_roles_tenant_id_index ON user_roles (app_id, tenant_id);

CREATE INDEX IF NOT EXISTS user_roles_app_id_role_index ON user_roles (app_id, role);

-- UserMetadata

ALTER TABLE user_metadata
  ADD COLUMN IF NOT EXISTS app_id VARCHAR(64) DEFAULT 'public';

ALTER TABLE user_metadata
  DROP CONSTRAINT user_metadata_pkey CASCADE;

ALTER TABLE user_metadata
  ADD CONSTRAINT user_metadata_pkey
    PRIMARY KEY (app_id, user_id);

ALTER TABLE user_metadata
  DROP CONSTRAINT IF EXISTS user_metadata_app_id_fkey;

ALTER TABLE user_metadata
  ADD CONSTRAINT user_metadata_app_id_fkey
    FOREIGN KEY (app_id)
    REFERENCES apps (app_id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS user_metadata_app_id_index ON user_metadata (app_id);

-- Dashboard

ALTER TABLE dashboard_users
  ADD COLUMN IF NOT EXISTS app_id VARCHAR(64) DEFAULT 'public';

ALTER TABLE dashboard_users
  DROP CONSTRAINT dashboard_users_pkey CASCADE;

ALTER TABLE dashboard_users
  ADD CONSTRAINT dashboard_users_pkey
    PRIMARY KEY (app_id, user_id);

ALTER TABLE dashboard_users
  DROP CONSTRAINT IF EXISTS dashboard_users_email_key;

ALTER TABLE dashboard_users
  ADD CONSTRAINT dashboard_users_email_key
    UNIQUE (app_id, email);

ALTER TABLE dashboard_users
  DROP CONSTRAINT IF EXISTS dashboard_users_app_id_fkey;

ALTER TABLE dashboard_users
  ADD CONSTRAINT dashboard_users_app_id_fkey
    FOREIGN KEY (app_id)
    REFERENCES apps (app_id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS dashboard_users_app_id_index ON dashboard_users (app_id);

------------------------------------------------------------

ALTER TABLE dashboard_user_sessions
  ADD COLUMN IF NOT EXISTS app_id VARCHAR(64) DEFAULT 'public';

ALTER TABLE dashboard_user_sessions
  DROP CONSTRAINT dashboard_user_sessions_pkey CASCADE;

ALTER TABLE dashboard_user_sessions
  ADD CONSTRAINT dashboard_user_sessions_pkey
    PRIMARY KEY (app_id, session_id);

ALTER TABLE dashboard_user_sessions
  DROP CONSTRAINT IF EXISTS dashboard_user_sessions_user_id_fkey;

ALTER TABLE dashboard_user_sessions
  ADD CONSTRAINT dashboard_user_sessions_user_id_fkey
    FOREIGN KEY (app_id, user_id)
    REFERENCES dashboard_users (app_id, user_id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS dashboard_user_sessions_user_id_index ON dashboard_user_sessions (app_id, user_id);

-- TOTP

ALTER TABLE totp_users
  ADD COLUMN IF NOT EXISTS app_id VARCHAR(64) DEFAULT 'public';

ALTER TABLE totp_users
  DROP CONSTRAINT totp_users_pkey CASCADE;

ALTER TABLE totp_users
  ADD CONSTRAINT totp_users_pkey
    PRIMARY KEY (app_id, user_id);

ALTER TABLE totp_users
  DROP CONSTRAINT IF EXISTS totp_users_app_id_fkey;

ALTER TABLE totp_users
  ADD CONSTRAINT totp_users_app_id_fkey
    FOREIGN KEY (app_id)
    REFERENCES apps (app_id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS totp_users_app_id_index ON totp_users (app_id);

------------------------------------------------------------

ALTER TABLE totp_user_devices
  ADD COLUMN IF NOT EXISTS app_id VARCHAR(64) DEFAULT 'public';

ALTER TABLE totp_user_devices
  DROP CONSTRAINT totp_user_devices_pkey;

ALTER TABLE totp_user_devices
  ADD CONSTRAINT totp_user_devices_pkey
    PRIMARY KEY (app_id, user_id, device_name);

ALTER TABLE totp_user_devices
  DROP CONSTRAINT IF EXISTS totp_user_devices_user_id_fkey;

ALTER TABLE totp_user_devices
  ADD CONSTRAINT totp_user_devices_user_id_fkey
    FOREIGN KEY (app_id, user_id)
    REFERENCES totp_users (app_id, user_id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS totp_user_devices_user_id_index ON totp_user_devices (app_id, user_id);

------------------------------------------------------------

ALTER TABLE totp_used_codes
  ADD COLUMN IF NOT EXISTS app_id VARCHAR(64) DEFAULT 'public',
  ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(64) DEFAULT 'public';

ALTER TABLE totp_used_codes
  DROP CONSTRAINT totp_used_codes_pkey CASCADE;

ALTER TABLE totp_used_codes
  ADD CONSTRAINT totp_used_codes_pkey
    PRIMARY KEY (app_id, tenant_id, user_id, created_time_ms);

ALTER TABLE totp_used_codes
  DROP CONSTRAINT IF EXISTS totp_used_codes_user_id_fkey;

ALTER TABLE totp_used_codes
  ADD CONSTRAINT totp_used_codes_user_id_fkey
    FOREIGN KEY (app_id, user_id)
    REFERENCES totp_users (app_id, user_id) ON DELETE CASCADE;

ALTER TABLE totp_used_codes
  DROP CONSTRAINT IF EXISTS totp_used_codes_tenant_id_fkey;

ALTER TABLE totp_used_codes
  ADD CONSTRAINT totp_used_codes_tenant_id_fkey
    FOREIGN KEY (app_id, tenant_id)
    REFERENCES tenants (app_id, tenant_id) ON DELETE CASCADE;

DROP INDEX IF EXISTS totp_used_codes_expiry_time_ms_index;

CREATE INDEX IF NOT EXISTS totp_used_codes_expiry_time_ms_index ON totp_used_codes (app_id, tenant_id, expiry_time_ms);

CREATE INDEX IF NOT EXISTS totp_used_codes_user_id_index ON totp_used_codes (app_id, user_id);

CREATE INDEX IF NOT EXISTS totp_used_codes_tenant_id_index ON totp_used_codes (app_id, tenant_id);

-- ActiveUsers

ALTER TABLE user_last_active
  ADD COLUMN IF NOT EXISTS app_id VARCHAR(64) DEFAULT 'public';

ALTER TABLE user_last_active
  DROP CONSTRAINT user_last_active_pkey CASCADE;

ALTER TABLE user_last_active
  ADD CONSTRAINT user_last_active_pkey
    PRIMARY KEY (app_id, user_id);

ALTER TABLE user_last_active
  DROP CONSTRAINT IF EXISTS user_last_active_app_id_fkey;

ALTER TABLE user_last_active
  ADD CONSTRAINT user_last_active_app_id_fkey
    FOREIGN KEY (app_id)
    REFERENCES apps (app_id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS user_last_active_app_id_index ON user_last_active (app_id);
