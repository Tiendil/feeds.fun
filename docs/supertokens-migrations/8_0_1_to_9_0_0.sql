ALTER TABLE totp_user_devices ADD COLUMN IF NOT EXISTS created_at BIGINT default 0;
ALTER TABLE totp_user_devices
  ALTER COLUMN created_at DROP DEFAULT;
