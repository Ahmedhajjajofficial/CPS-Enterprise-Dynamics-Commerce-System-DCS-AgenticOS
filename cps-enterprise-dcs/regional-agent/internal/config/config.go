/*
Configuration - Regional Agent Settings
=======================================
Centralized configuration management.
*/

package config

// Config holds all configuration for the regional agent
type Config struct {
	// Identity
	AgentID  string
	RegionID string

	// Network
	RPCAddress  string
	RaftAddress string
	GRPCPort    int

	// Storage
	DataDir       string
	PostgreSQLURL string
	RedisURL      string

	// Consensus
	Bootstrap    bool
	JoinAddress  string
	ClusterNodes []string

	// Security
	TLSCertFile string
	TLSKeyFile  string
	TLSCAFile   string

	// Performance
	MaxConnections    int
	BatchSize         int
	SyncIntervalSec   int
	ForecastInterval  int
}

// DefaultConfig returns a configuration with sensible defaults
func DefaultConfig() *Config {
	return &Config{
		GRPCPort:         50052,
		MaxConnections:   1000,
		BatchSize:        100,
		SyncIntervalSec:  30,
		ForecastInterval: 3600, // 1 hour
	}
}

// Validate checks if the configuration is valid
func (c *Config) Validate() error {
	if c.AgentID == "" {
		return ErrMissingAgentID
	}
	if c.RegionID == "" {
		return ErrMissingRegionID
	}
	if c.RPCAddress == "" {
		c.RPCAddress = ":12000"
	}
	if c.RaftAddress == "" {
		c.RaftAddress = ":12001"
	}
	return nil
}

// Errors
var (
	ErrMissingAgentID  = &ConfigError{Field: "AgentID", Message: "agent ID is required"}
	ErrMissingRegionID = &ConfigError{Field: "RegionID", Message: "region ID is required"}
)

// ConfigError represents a configuration error
type ConfigError struct {
	Field   string
	Message string
}

func (e *ConfigError) Error() string {
	return e.Message
}
