package api

import (
	"net/http"

	"github.com/gin-gonic/gin"
	agentgrpc "maigokite/gateway/internal/grpc"
)

type AuditHandler struct{ client *agentgrpc.AgentClient }

func (h *AuditHandler) List(c *gin.Context) {
	events, err := h.client.ListAuditEvents(c.Request.Context(), c.Param("workspaceID"))
	if err != nil {
		grpcError(c, err)
		return
	}
	c.JSON(http.StatusOK, events)
}
