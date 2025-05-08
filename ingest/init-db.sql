-- Create the `frames` table to hold one row per file
CREATE TABLE IF NOT EXISTS frames (
    station     TEXT                NOT NULL,
    resolution  TEXT                NOT NULL,
    timestamp   TIMESTAMPTZ         NOT NULL,
    key         TEXT                NOT NULL,  -- S3 key, SSHFS-relative path, etc.
    PRIMARY KEY (station, resolution, timestamp)
);

-- Index on timestamp for fast time-range queries
CREATE INDEX IF NOT EXISTS idx_frames_timestamp
    ON frames (timestamp);