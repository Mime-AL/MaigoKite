package api

import (
	"encoding/json"
	"io"
	"net/http"

	"github.com/gin-gonic/gin"
	agentgrpc "maigokite/gateway/internal/grpc"
	agentv1 "maigokite/gateway/pkg/proto/agent/v1"
)

type PermissionHandler struct{ client *agentgrpc.AgentClient }

type permissionSettingsRequest struct {
	DefaultMode string `json:"default_mode"`
}

func permissionSettingsValue(item *agentv1.PermissionSettings) gin.H {
	return gin.H{"default_mode": item.DefaultMode}
}

func (h *PermissionHandler) Get(c *gin.Context) {
	item, err := h.client.GetPermissionSettings(c.Request.Context(), c.Param("workspaceID"))
	if err != nil {
		grpcError(c, err)
		return
	}
	c.JSON(http.StatusOK, permissionSettingsValue(item))
}

func (h *PermissionHandler) Update(c *gin.Context) {
	var req permissionSettingsRequest
	// Do not silently accept removed settings such as tool_levels or grants.
	decoder := json.NewDecoder(http.MaxBytesReader(c.Writer, c.Request.Body, 4096))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "VALIDATION", "message": err.Error()}})
		return
	}
	if err := decoder.Decode(&struct{}{}); err != io.EOF {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "VALIDATION", "message": "expected a single JSON object"}})
		return
	}
	switch req.DefaultMode {
	case "read_only", "workspace", "workspace_auto", "full_access", "danger_full_access":
	default:
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "VALIDATION", "message": "default_mode must be read_only, workspace, workspace_auto or danger_full_access; full_access is a legacy restricted alias"}})
		return
	}
	item, err := h.client.UpdatePermissionSettings(c.Request.Context(), c.Param("workspaceID"), &agentv1.PermissionSettings{
		DefaultMode: req.DefaultMode,
	})
	if err != nil {
		grpcError(c, err)
		return
	}
	c.JSON(http.StatusOK, permissionSettingsValue(item))
}
