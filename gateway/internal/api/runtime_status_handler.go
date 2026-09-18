package api

import (
	"context"
	"os"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/nanamigopher/nanamigopher/gateway/internal/config"
	agentv1 "github.com/nanamigopher/nanamigopher/gateway/pkg/proto/agent/v1"
)

type agentHealthReader interface {
	Health(context.Context) (*agentv1.HealthResponse, error)
}

type runtimeServiceStatus struct {
	Status  string `json:"status"`
	Version string `json:"version,omitempty"`
}

type restartPolicy struct {
	Pending     bool     `json:"pending"`
	RequiredFor []string `json:"required_for"`
	HotApplied  []string `json:"hot_applied"`
	Note        string   `json:"note"`
}

type runtimeStatusResponse struct {
	WorkspaceID     string               `json:"workspace_id"`
	WorkspaceRoot   string               `json:"workspace_root"`
	WorkspaceSource string               `json:"workspace_source"`
	Environment     string               `json:"environment"`
	Gateway         runtimeServiceStatus `json:"gateway"`
	AgentCore       runtimeServiceStatus `json:"agent_core"`
	Restart         restartPolicy        `json:"restart"`
}

type RuntimeStatusHandler struct {
	app           config.AppConfig
	workspaceRoot string
	rootSource    string
	client        agentHealthReader
}

func newRuntimeStatusHandler(cfg *config.Config, workspace *WorkspaceHandler, client agentHealthReader) *RuntimeStatusHandler {
	rootSource := "configuration"
	if strings.TrimSpace(os.Getenv("NANAMI_WORKSPACE_ROOT")) != "" {
		rootSource = "environment"
	}
	return &RuntimeStatusHandler{
		app: cfg.App, workspaceRoot: workspace.root, rootSource: rootSource, client: client,
	}
}

func (h *RuntimeStatusHandler) Get(c *gin.Context) {
	core := runtimeServiceStatus{Status: "unavailable"}
	if h.client != nil {
		ctx, cancel := context.WithTimeout(c.Request.Context(), 2*time.Second)
		defer cancel()
		if health, err := h.client.Health(ctx); err == nil && health != nil {
			core.Status = health.Status
			core.Version = health.Version
		}
	}
	c.JSON(200, runtimeStatusResponse{
		WorkspaceID:     c.Param("workspaceID"),
		WorkspaceRoot:   h.workspaceRoot,
		WorkspaceSource: h.rootSource,
		Environment:     h.app.Env,
		Gateway:         runtimeServiceStatus{Status: "serving", Version: h.app.Version},
		AgentCore:       core,
		Restart: restartPolicy{
			Pending:     false,
			RequiredFor: []string{"Workspace 根目录", "MCP Server 启动配置", "Gateway / Agent Core 端口"},
			HotApplied:  []string{"Chat 模型与默认模型", "联网工具凭证", "权限模式", "界面称呼"},
			Note:        "当前设置页没有待重启更改；外部 YAML 或环境变量修改由下次启动加载。",
		},
	})
}
