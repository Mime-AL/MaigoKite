// Package mcp provides management of MCP Server processes.
// MCP Servers are launched as child processes and communicate via stdio
// using the Model Context Protocol (JSON-RPC over stdin/stdout).
package mcp

import (
	"context"
	"fmt"
	"os/exec"
	"sync"
)

// MCPServer represents a single MCP Server process managed by the gateway.
type MCPServer struct {
	name       string
	command    string
	args       []string
	env        []string
	cmd        *exec.Cmd
	isRunning  bool
	mu         sync.Mutex
}

// Manager orchestrates the lifecycle of all MCP Server processes.
type Manager struct {
	servers map[string]*MCPServer
	config  *ServerConfig
	mu      sync.RWMutex
}

// ServerConfig holds MCP server configuration entries.
type ServerConfig struct {
	Command     string
	Args        []string
	EnvKeyName  string
	AutoInstall bool
	HealthCheck string
}

// NewManager creates a new MCP Manager with the given configuration.
func NewManager(config map[string]ServerConfig) *Manager {
	return &Manager{
		servers: make(map[string]*MCPServer),
		config:  nil, // TODO: convert map to struct
	}
}

// StartServer launches an MCP Server process by name.
func (m *Manager) StartServer(ctx context.Context, name string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	if _, ok := m.servers[name]; ok {
		return fmt.Errorf("server %s already running", name)
	}

	// TODO: read config, resolve API keys from credential store, build command
	_ = ctx
	return nil
}

// StopServer terminates an MCP Server process.
func (m *Manager) StopServer(name string) {
	m.mu.Lock()
	defer m.mu.Unlock()

	if server, ok := m.servers[name]; ok {
		server.mu.Lock()
		if server.isRunning && server.cmd != nil && server.cmd.Process != nil {
			server.cmd.Process.Kill()
		}
		server.isRunning = false
		server.mu.Unlock()
		delete(m.servers, name)
	}
}

// RestartServer stops and restarts an MCP Server (used for config changes).
func (m *Manager) RestartServer(ctx context.Context, name string) error {
	m.StopServer(name)
	return m.StartServer(ctx, name)
}

// IsHealthy checks whether an MCP Server is alive and responsive.
func (m *Manager) IsHealthy(name string) bool {
	m.mu.RLock()
	defer m.mu.RUnlock()

	server, ok := m.servers[name]
	if !ok {
		return false
	}

	server.mu.Lock()
	defer server.mu.Unlock()

	if !server.isRunning {
		return false
	}

	// TODO: implement HTTP health check if healthURL is configured
	return true
}

// ListServers returns the names of all currently running MCP servers.
func (m *Manager) ListServers() []string {
	m.mu.RLock()
	defer m.mu.RUnlock()

	names := make([]string, 0, len(m.servers))
	for name := range m.servers {
		names = append(names, name)
	}
	return names
}
