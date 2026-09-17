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
	} {
		if !routes[expected] {
			t.Fatalf("expected route %q to be registered", expected)
		}
	}
}
