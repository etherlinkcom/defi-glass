CREATE TABLE tvl_history (
    protocol TEXT NOT NULL,
    type TEXT NOT NULL,
    token TEXT NOT NULL,
    amount DOUBLE PRECISION NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    address TEXT NOT NULL
);

CREATE INDEX idx_tvl_protocol ON tvl_history (protocol);
CREATE INDEX idx_tvl_type ON tvl_history (type);
CREATE INDEX idx_tvl_token ON tvl_history (token);
CREATE INDEX idx_tvl_timestamp ON tvl_history (timestamp);
CREATE INDEX idx_tvl_address ON tvl_history (address);
