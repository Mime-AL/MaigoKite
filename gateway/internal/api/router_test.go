package api

import (
	"testing"

	"github.com/nanamigopher/nanamigopher/gateway/internal/config"
	"github.com/nanamigopher/nanamigopher/gateway/internal/observability"
)

func TestNewRouterRegistersDistinctModelActionRoutes(t *testing.T) {
	engine := NewRouter(
		config.DefaultConfig(),
		observability.NewConsoleObserver("router-test"),
		nil,
	)

	routes := make(map[string]bool)
	for _, route := range engine.Routes() {
		routes[route.Method+" "+route.Path] = true
	}

	for _, expected := range []string{
		"POST /api/v1/workspaces/:workspaceID/models/actions/validate",
		"POST /api/v1/workspaces/:workspaceID/models/actions/discover",
		"GET /api/v1/workspaces/:workspaceID/runtime-status",
		"GET /api/v1/workspaces/:workspaceID/memories",
		"POST /api/v1/workspaces/:workspaceID/memories",
		"PATCH /api/v1/workspaces/:workspaceID/memories/:memoryID",
		"DELETE /api/v1/workspaces/:workspaceID/memories/:memoryID",
		"GET /api/v1/workspaces/:workspaceID/data-summary",
		"GET /api/v1/workspaces/:workspaceID/mcp-servers",
		"GET /api/v1/workspaces/:workspaceID/skills",
		"GET /api/v1/workspaces/:workspaceID/tasks",
		"GET /api/v1/workspaces/:workspaceID/tasks/:taskID",
		"POST /api/v1/workspaces/:workspaceID/tasks/:taskID/cancel",
		"GET /api/v1/workspaces/:workspaceID/conversations/:conversationID/events/history",
	} {
		if !routes[expected] {
			t.Fatalf("expected route %q to be registered", expected)
		}
	}
}
