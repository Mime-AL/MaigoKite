package api

import (
	"net/http"

	"github.com/gin-gonic/gin"
	agentgrpc "maigokite/gateway/internal/grpc"
)

// PreferenceHandler exposes non-secret, per-user interface preferences.
type PreferenceHandler struct {
	client *agentgrpc.AgentClient
}

type preferenceUpdateRequest struct {
	AssistantName string `json:"assistant_name" binding:"required,max=32"`
}

func (h *PreferenceHandler) Get(c *gin.Context) {
	item, err := h.client.GetUserPreferences(c.Request.Context(), c.Param("workspaceID"), c.GetString("principal_id"))
	if err != nil {
		grpcError(c, err)
		return
	}
	c.JSON(http.StatusOK, gin.H{"assistant_name": item.AssistantName})
}

func (h *PreferenceHandler) Update(c *gin.Context) {
	var req preferenceUpdateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "VALIDATION", "message": err.Error()}})
		return
	}
	item, err := h.client.UpdateUserPreferences(
		c.Request.Context(), c.Param("workspaceID"), c.GetString("principal_id"), req.AssistantName,
	)
	if err != nil {
		grpcError(c, err)
		return
	}
	_ = h.client.RecordAuditEvent(c.Request.Context(), c.Param("workspaceID"), c.GetString("principal_id"), "user.preferences.updated", "interface", "success")
	c.JSON(http.StatusOK, gin.H{"assistant_name": item.AssistantName})
}
