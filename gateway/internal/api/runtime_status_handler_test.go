package api

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"maigokite/gateway/internal/config"
	agentv1 "maigokite/gateway/pkg/proto/agent/v1"
)

type fakeAgentHealth struct {
	response *agentv1.HealthResponse
	err      error
}

func (f fakeAgentHealth) Health(context.Context) (*agentv1.HealthResponse, error) {
	return f.response, f.err
}

func TestRuntimeStatusReturnsCanonicalWorkspaceAndCoreHealth(t *testing.T) {
	gin.SetMode(gin.TestMode)
	root := t.TempDir()
	cfg := config.DefaultConfig()
	cfg.Workspace.Root = root
	cfg.App.Version = "0.1-test"
	handler := newRuntimeStatusHandler(
		cfg,
		newWorkspaceHandler(root),
		fakeAgentHealth{response: &agentv1.HealthResponse{Status: "serving", Version: "core-test"}},
	)
	router := gin.New()
	router.GET("/workspaces/:workspaceID/runtime-status", handler.Get)

	recorder := httptest.NewRecorder()
	router.ServeHTTP(recorder, httptest.NewRequest(http.MethodGet, "/workspaces/personal/runtime-status", nil))

	if recorder.Code != http.StatusOK {
		t.Fatalf("unexpected status %d", recorder.Code)
	}
	var response runtimeStatusResponse
	if err := json.Unmarshal(recorder.Body.Bytes(), &response); err != nil {
		t.Fatal(err)
	}
	if response.WorkspaceRoot != root || response.WorkspaceID != "personal" {
		t.Fatalf("unexpected workspace status: %#v", response)
	}
	if response.Gateway.Status != "serving" || response.Gateway.Version != "0.1-test" {
		t.Fatalf("unexpected Gateway status: %#v", response.Gateway)
	}
	if response.AgentCore.Status != "serving" || response.AgentCore.Version != "core-test" {
		t.Fatalf("unexpected Agent Core status: %#v", response.AgentCore)
	}
	if response.Restart.Pending {
		t.Fatal("read-only runtime status must not invent pending changes")
	}
}

func TestRuntimeStatusDegradesCoreWithoutFailingGatewayRequest(t *testing.T) {
	gin.SetMode(gin.TestMode)
	cfg := config.DefaultConfig()
	handler := newRuntimeStatusHandler(cfg, newWorkspaceHandler(t.TempDir()), fakeAgentHealth{err: context.DeadlineExceeded})
	router := gin.New()
	router.GET("/workspaces/:workspaceID/runtime-status", handler.Get)

	recorder := httptest.NewRecorder()
	router.ServeHTTP(recorder, httptest.NewRequest(http.MethodGet, "/workspaces/personal/runtime-status", nil))

	if recorder.Code != http.StatusOK {
		t.Fatalf("unexpected status %d", recorder.Code)
	}
	var response runtimeStatusResponse
	if err := json.Unmarshal(recorder.Body.Bytes(), &response); err != nil {
		t.Fatal(err)
	}
	if response.Gateway.Status != "serving" || response.AgentCore.Status != "unavailable" {
		t.Fatalf("unexpected degraded status: %#v", response)
	}
}
