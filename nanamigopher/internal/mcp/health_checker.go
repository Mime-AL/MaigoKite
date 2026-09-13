// Package mcp provides health checking for MCP Server processes.
package mcp

import (
	"context"
	"net/http"
	"time"
)

// HealthChecker periodically verifies the health of managed MCP servers.
type HealthChecker struct {
	manager *Manager
	interval time.Duration
	client   *http.Client
}

// NewHealthChecker creates a new health checker for the given manager.
func NewHealthChecker(manager *Manager, interval time.Duration) *HealthChecker {
	return &HealthChecker{
		manager:  manager,
		interval: interval,
		client:   &http.Client{Timeout: 5 * time.Second},
	}
}

// Start begins periodic health checks in a goroutine.
func (hc *HealthChecker) Start(ctx context.Context) {
	ticker := time.NewTicker(hc.interval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			hc.checkAll()
		}
	}
}

func (hc *HealthChecker) checkAll() {
	// TODO: iterate running servers, check health URLs
	_ = hc.client
}

// CheckServer performs a single health check on a named server.
func (hc *HealthChecker) CheckServer(name string) bool {
	// TODO: implement HTTP health check against server's health URL
	return hc.manager.IsHealthy(name)
}
