package api

import (
	"context"
	"encoding/json"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	agentgrpc "github.com/nanamigopher/nanamigopher/gateway/internal/grpc"
	ws "github.com/nanamigopher/nanamigopher/gateway/internal/websocket"
	agentv1 "github.com/nanamigopher/nanamigopher/gateway/pkg/proto/agent/v1"
)

type ApprovalHandler struct {
	client *agentgrpc.AgentClient
	hub    *ws.Hub
}

type approvalResponse struct {
	ID             string         `json:"id"`
	WorkspaceID    string         `json:"workspace_id"`
	ConversationID string         `json:"conversation_id"`
	TaskID         string         `json:"task_id"`
	ToolCallID     string         `json:"tool_call_id"`
	ToolName       string         `json:"tool_name"`
	Arguments      map[string]any `json:"arguments"`
	ResourceScope  string         `json:"resource_scope"`
	RiskLevel      string         `json:"risk_level"`
	Status         string         `json:"status"`
	Version        int32          `json:"version"`
	ExpiresAt      string         `json:"expires_at"`
}

func approvalValue(item *agentv1.Approval) approvalResponse {
	arguments := map[string]any{}
	_ = json.Unmarshal([]byte(item.ArgumentsJson), &arguments)
	return approvalResponse{
		ID: item.Id, WorkspaceID: item.WorkspaceId, ConversationID: item.ConversationId,
		TaskID: item.TaskId, ToolCallID: item.ToolCallId, ToolName: item.ToolName,
		Arguments: arguments, ResourceScope: item.ResourceScope, RiskLevel: item.RiskLevel,
		Status: item.Status, Version: item.Version, ExpiresAt: item.ExpiresAt,
	}
}

func (h *ApprovalHandler) List(c *gin.Context) {
	items, err := h.client.ListApprovals(c.Request.Context(), c.Param("workspaceID"), c.Query("conversation_id"))
	if err != nil {
		grpcError(c, err)
		return
	}
	result := make([]approvalResponse, 0, len(items.Approvals))
	for _, item := range items.Approvals {
		result = append(result, approvalValue(item))
	}
	c.JSON(http.StatusOK, gin.H{"approvals": result})
}

type approvalDecisionRequest struct {
	Decision string `json:"decision" binding:"required,oneof=allow deny"`
	Version  int32  `json:"version" binding:"required,min=1"`
}

func (h *ApprovalHandler) Decide(c *gin.Context) {
	var req approvalDecisionRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "VALIDATION", "message": err.Error()}})
		return
	}
	streamContext, cancel := context.WithTimeout(context.Background(), 10*time.Minute)
	events, errs := h.client.DecideApproval(streamContext, &agentv1.ApprovalDecisionRequest{
		WorkspaceId: c.Param("workspaceID"), ApprovalId: c.Param("approvalID"),
		PrincipalId: c.GetString("principal_id"), Decision: req.Decision, Version: req.Version,
	})
	first, ok := <-events
	if !ok {
		cancel()
		if err := <-errs; err != nil {
			grpcError(c, err)
			return
		}
		c.JSON(http.StatusBadGateway, gin.H{"error": gin.H{"code": "EMPTY_STREAM", "message": "agent returned no event"}})
		return
	}
	broadcast := func(event *agentv1.AgentEvent) {
		payload := json.RawMessage(event.PayloadJson)
		if len(payload) == 0 || !json.Valid(payload) {
			payload, _ = json.Marshal(gin.H{"content": event.Content, "message": event.Message, "code": event.Code})
		}
		h.hub.BroadcastEvent(event.ConversationId, event.TaskId, event.Type, payload)
	}
	broadcast(first)
	go func() {
		defer cancel()
		for event := range events {
			broadcast(event)
		}
		for range errs {
		}
	}()
	c.JSON(http.StatusAccepted, gin.H{"approval_id": c.Param("approvalID"), "task_id": first.TaskId, "status": "processing"})
}
