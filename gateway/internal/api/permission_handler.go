package api

import (
	"net/http"

	"github.com/gin-gonic/gin"
	agentgrpc "github.com/nanamigopher/nanamigopher/gateway/internal/grpc"
	agentv1 "github.com/nanamigopher/nanamigopher/gateway/pkg/proto/agent/v1"
)

type PermissionHandler struct{ client *agentgrpc.AgentClient }

type permissionSettingsRequest struct {
	DefaultMode string `json:"default_mode" binding:"required,oneof=read_only workspace full_access"`
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
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "VALIDATION", "message": err.Error()}})
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
