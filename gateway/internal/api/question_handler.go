package api

import (
	"context"
	"encoding/json"
	"net/http"

	"github.com/gin-gonic/gin"
	"maigokite/gateway/internal/credentialstore"
	agentgrpc "maigokite/gateway/internal/grpc"
	ws "maigokite/gateway/internal/websocket"
	agentv1 "maigokite/gateway/pkg/proto/agent/v1"
)

type QuestionHandler struct {
	client *agentgrpc.AgentClient
	hub    *ws.Hub
	mgr    *credentialstore.Manager
}

func (h *QuestionHandler) List(c *gin.Context) {
	items, err := h.client.ListQuestions(c.Request.Context(), c.Param("workspaceID"), c.Query("conversation_id"))
	if err != nil {
		grpcError(c, err)
		return
	}
	result := make([]gin.H, 0, len(items.Questions))
	for _, item := range items.Questions {
		options := []any{}
		_ = json.Unmarshal([]byte(item.OptionsJson), &options)
		result = append(result, gin.H{
			"id": item.Id, "workspace_id": item.WorkspaceId, "conversation_id": item.ConversationId,
			"task_id": item.TaskId, "tool_call_id": item.ToolCallId, "title": item.Title,
			"options": options, "status": item.Status, "version": item.Version, "created_at": item.CreatedAt,
		})
	}
	c.JSON(http.StatusOK, gin.H{"questions": result})
}

func (h *QuestionHandler) Answer(c *gin.Context) {
	var req struct {
		Answer  string `json:"answer" binding:"required,max=10000"`
		Version int32  `json:"version" binding:"required,min=1"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "VALIDATION", "message": err.Error()}})
		return
	}
	items, err := h.client.ListQuestions(c.Request.Context(), c.Param("workspaceID"), "")
	if err != nil {
		grpcError(c, err)
		return
	}
	var pending *agentv1.Question
	for _, item := range items.Questions {
		if item.Id == c.Param("questionID") {
			pending = item
			break
		}
	}
	if pending == nil || pending.Version != req.Version {
		c.JSON(http.StatusConflict, gin.H{"error": gin.H{"code": "QUESTION_NOT_PENDING", "message": "question is no longer pending; refresh its status"}})
		return
	}
	if err := prepareExecutionCredentials(c.Request.Context(), h.client, h.mgr, c.Param("workspaceID"), pending.ConversationId, pending.TaskId); err != nil {
		grpcError(c, err)
		return
	}
	ctx, cancel := context.WithCancel(context.Background())
	events, errs := h.client.AnswerQuestion(ctx, &agentv1.QuestionAnswerRequest{
		WorkspaceId: c.Param("workspaceID"), QuestionId: pending.Id, PrincipalId: c.GetString("principal_id"),
		Answer: req.Answer, Version: req.Version,
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
	if first.Type == "error" {
		cancel()
		c.JSON(http.StatusBadGateway, gin.H{"error": gin.H{"code": first.Code, "message": first.Message}})
		return
	}
	forwardExecutionEvents(h.hub, first, events, errs, cancel)
	c.JSON(http.StatusAccepted, gin.H{"question_id": pending.Id, "task_id": first.TaskId, "status": "processing"})
}
