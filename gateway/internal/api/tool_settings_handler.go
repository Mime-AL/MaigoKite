package api

import (
	"net/http"

	"github.com/gin-gonic/gin"
	agentgrpc "github.com/nanamigopher/nanamigopher/gateway/internal/grpc"
	agentv1 "github.com/nanamigopher/nanamigopher/gateway/pkg/proto/agent/v1"
)

type ToolSettingsHandler struct{ client *agentgrpc.AgentClient }

func toolSettingsValue(settings *agentv1.ToolSettings) gin.H {
	items := make([]gin.H, 0, len(settings.Tools))
	for _, tool := range settings.Tools {
		items = append(items, gin.H{
			"name": tool.Name, "description": tool.Description, "source": tool.Source,
			"enabled": tool.Enabled, "configurable": tool.Configurable, "default_enabled": tool.DefaultEnabled,
		})
	}
	return gin.H{"tools": items}
}

func (h *ToolSettingsHandler) Get(c *gin.Context) {
	settings, err := h.client.GetToolSettings(c.Request.Context(), c.Param("workspaceID"))
	if err != nil {
		grpcError(c, err)
		return
	}
	c.JSON(http.StatusOK, toolSettingsValue(settings))
}

func (h *ToolSettingsHandler) Update(c *gin.Context) {
	var req struct {
		Enabled map[string]*bool `json:"enabled" binding:"required"`
	}
	c.Request.Body = http.MaxBytesReader(c.Writer, c.Request.Body, 64<<10)
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "VALIDATION", "message": err.Error()}})
		return
	}
	enabled := make(map[string]bool, len(req.Enabled))
	for name, value := range req.Enabled {
		if value == nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "VALIDATION", "message": "tool selection must be boolean"}})
			return
		}
		enabled[name] = *value
	}
	settings, err := h.client.UpdateToolSettings(c.Request.Context(), c.Param("workspaceID"), enabled)
	if err != nil {
		grpcError(c, err)
		return
	}
	c.JSON(http.StatusOK, toolSettingsValue(settings))
}
