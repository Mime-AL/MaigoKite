// Package config provides configuration loading and management for the gateway.
// It reads YAML config files and supports environment variable overrides.
package config

import (
	"fmt"
	"os"
	"path/filepath"
	"strconv"

	"gopkg.in/yaml.v3"
)

// Config holds all application configuration.
type Config struct {
	App           AppConfig           `yaml:"app"`
	Models        ModelsConfig        `yaml:"models"`
	Memory        MemoryConfig        `yaml:"memory"`
	Security      SecurityConfig      `yaml:"security"`
	Skills        SkillsConfig        `yaml:"skills"`
	MCP           MCPConfig           `yaml:"mcp"`
	Observability ObservabilityConfig `yaml:"observability"`
	GRPC          GRPCConfig          `yaml:"grpc"`
	HTTP          HTTPConfig          `yaml:"http"`
	Workspace     WorkspaceConfig     `yaml:"workspace"`
}

// AppConfig holds application-level settings.
type AppConfig struct {
	Name    string `yaml:"name"`
	Version string `yaml:"version"`
	Env     string `yaml:"environment"`
	Debug   bool   `yaml:"debug"`
}

// ChatModelConfig holds chat model configuration.
type ChatModelConfig struct {
	Provider       string  `yaml:"provider"`
	Default        string  `yaml:"default"`
	Fallback       string  `yaml:"fallback"`
	BaseURL        string  `yaml:"base_url"`
	Temperature    float64 `yaml:"temperature"`
	MaxTokens      int     `yaml:"max_tokens"`
	TimeoutSeconds int     `yaml:"timeout_seconds"`
}

// BGEConfig holds BGE embedding model specifics.
type BGEConfig struct {
	Model  string `yaml:"model"`
	Device string `yaml:"device"`
}

// EmbeddingConfig holds embedding model configuration.
type EmbeddingConfig struct {
	Provider string    `yaml:"provider"`
	BGE      BGEConfig `yaml:"bge,omitempty"`
}

// ModelsConfig holds model provider settings.
type ModelsConfig struct {
	PreferLocal        bool            `yaml:"prefer_local"`
	LocalFallbackOrder []string        `yaml:"local_fallback_order"`
	Chat               ChatModelConfig `yaml:"chat"`
	Embedding          EmbeddingConfig `yaml:"embedding"`
}

// MemoryConfig holds memory system settings.
type MemoryConfig struct {
	Storage MemoryStorageConfig `yaml:"storage"`
}

type MemoryStorageConfig struct {
	SQLitePath string `yaml:"sqlite_path"`
	VectorDB   string `yaml:"vector_db"`
}

// SecurityConfig holds security filter settings.
type SecurityConfig struct {
	PromptInjection PromptInjectionConfig `yaml:"prompt_injection"`
	AuditLog        AuditLogConfig        `yaml:"audit_log"`
}

type PromptInjectionConfig struct {
	Enabled     bool              `yaml:"enabled"`
	LengthLimit LengthLimitConfig `yaml:"length_limit"`
	Whitelist   WhitelistConfig   `yaml:"whitelist"`
}

type LengthLimitConfig struct {
	MaxTokens int    `yaml:"max_tokens"`
	Strategy  string `yaml:"strategy"`
}

type WhitelistConfig struct {
	GlobalKeywords []string `yaml:"global_keywords"`
	UserKeywords   []string `yaml:"user_keywords"`
}

type AuditLogConfig struct {
	Enabled       bool   `yaml:"enabled"`
	Path          string `yaml:"path"`
	RetentionDays int    `yaml:"retention_days"`
}

// SkillsConfig holds skill-related settings.
type SkillsConfig struct {
	ScanDirectories    []string `yaml:"scan_directories"`
	NamespaceIsolation bool     `yaml:"namespace_isolation"`
}

// MCPConfig holds MCP server settings.
type MCPConfig struct {
	Servers map[string]MCPServerConfig `yaml:"servers"`
}

type MCPServerConfig struct {
	Command     string   `yaml:"command"`
	Args        []string `yaml:"args"`
	EnvKeyName  string   `yaml:"env_key_name"`
	AutoInstall bool     `yaml:"auto_install"`
	HealthCheck string   `yaml:"health_check"`
}

// ObservabilityConfig holds observability settings.
type ObservabilityConfig struct {
	ConsoleOutput bool          `yaml:"console_output"`
	Tracing       TracingConfig `yaml:"tracing"`
}

type TracingConfig struct {
	Enabled    bool    `yaml:"enabled"`
	Provider   string  `yaml:"provider"`
	SampleRate float64 `yaml:"sample_rate"`
}

// GRPCConfig holds gRPC connection settings.
type GRPCConfig struct {
	Port    int `yaml:"port"`
	Timeout int `yaml:"timeout"`
}

// HTTPConfig holds HTTP server settings.
type HTTPConfig struct {
	Port int `yaml:"port"`
}

type WorkspaceConfig struct {
	Root string `yaml:"root"`
}

// Load reads configuration from a YAML file and applies environment overrides.
// If path is empty, returns default config.
func Load(path string) (*Config, error) {
	cfg := DefaultConfig()

	if path == "" {
		cfg.applyEnvOverrides()
		return cfg, nil
	}

	data, err := os.ReadFile(path)
	if err != nil {
		cfg.applyEnvOverrides()
		return cfg, nil
	}

	if err := yaml.Unmarshal(data, cfg); err != nil {
		return nil, fmt.Errorf("parse config: %w", err)
	}

	cfg.applyEnvOverrides()

	if err := cfg.Validate(); err != nil {
		return nil, fmt.Errorf("validate config: %w", err)
	}

	return cfg, nil
}

// DefaultConfig returns the default configuration values.
func DefaultConfig() *Config {
	return &Config{
		App: AppConfig{
			Name:    "MaigoKite",
			Version: "0.1.0",
			Env:     "development",
		},
		HTTP:      HTTPConfig{Port: 8080},
		GRPC:      GRPCConfig{Port: 8081, Timeout: 30},
		Workspace: WorkspaceConfig{Root: ""},
		Security: SecurityConfig{
			PromptInjection: PromptInjectionConfig{
				Enabled: true,
				LengthLimit: LengthLimitConfig{
					MaxTokens: 4096,
					Strategy:  "truncate",
				},
			},
		},
	}
}

// Validate checks configuration validity.
func (cfg *Config) Validate() error {
	if cfg.HTTP.Port <= 0 {
		return fmt.Errorf("http port must be positive")
	}
	if cfg.GRPC.Port <= 0 {
		return fmt.Errorf("grpc port must be positive")
	}
	return nil
}

// applyEnvOverrides applies environment variables to configuration.
func (cfg *Config) applyEnvOverrides() {
	if v := os.Getenv("NG_HTTP_PORT"); v != "" {
		if port, err := strconv.Atoi(v); err == nil {
			cfg.HTTP.Port = port
		}
	}
	if v := os.Getenv("NG_GRPC_PORT"); v != "" {
		if port, err := strconv.Atoi(v); err == nil {
			cfg.GRPC.Port = port
		}
	}
	if v := os.Getenv("NG_ENV"); v != "" {
		cfg.App.Env = v
	}
	if v := os.Getenv("MAIGOKITE_WORKSPACE_ROOT"); v != "" {
		cfg.Workspace.Root = v
	}
	if cfg.Workspace.Root == "" {
		// Launchers supply a shared absolute install directory. The file/status
		// handlers also resolve registered roots in Core, the workspace authority.
		cfg.Workspace.Root = filepath.Join(os.Getenv("MAIGOKITE_INSTALL_DIR"), ".workspace")
	}
}
