package api

import (
	"context"
	"net/http"

	"github.com/gin-gonic/gin"
	"maigokite/gateway/internal/credentialstore"
	agentgrpc "maigokite/gateway/internal/grpc"
	ws "maigokite/gateway/internal/websocket"
	agentv1 "maigokite/gateway/pkg/proto/agent/v1"
)

// TaskResumeHandler is transport/credential glue, not an execution scheduler.
// Core validates checkpoint eligibility and owns the resumed root task.
type TaskResumeHandler struct {
	client *agentgrpc.AgentClient
	hub    *ws.Hub
	mgr    *credentialstore.Manager
}

func (h *TaskResumeHandler) Resume(c *gin.Context) {
	var req struct {
		Version int32 `json:"version" binding:"required,min=1"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "VALIDATION", "message": err.Error()}})
		return
	}
	workspaceID, taskID := c.Param("workspaceID"), c.Param("taskID")
	task, err := h.client.GetTask(c.Request.Context(), workspaceID, taskID)
	if err != nil {
		grpcError(c, err)
		return
	}
	if task.Status != "interrupted" || task.Version != req.Version {
		c.JSON(http.StatusConflict, gin.H{"error": gin.H{"code": "TASK_NOT_RESUMABLE", "message": "task is not interrupted at this version; refresh its status"}})
		return
	}
	if err := prepareExecutionCredentials(c.Request.Context(), h.client, h.mgr, workspaceID, task.ConversationId, taskID); err != nil {
		grpcError(c, err)
		return
	}
	ctx, cancel := context.WithCancel(context.Background())
	events, errs := h.client.ResumeTask(ctx, &agentv1.ResumeTaskRequest{
		WorkspaceId: workspaceID, TaskId: taskID, PrincipalId: c.GetString("principal_id"), Version: req.Version,
	})
	first, ok := <-events
	if !ok {
		cancel()
		if err := <-errs; err != nil {
			grpcError(c, err)
			return
		}
		c.JSON(http.StatusBadGateway, gin.H{"error": gin.H{"code": "EMPTY_STREAM", "message": "agent returned no recovery acknowledgement"}})
		return
	}
	if first.Type != "task.resumed" || first.TaskId != taskID || first.ConversationId != task.ConversationId {
		cancel()
		c.JSON(http.StatusBadGateway, gin.H{"error": gin.H{"code": "INVALID_RECOVERY_STREAM", "message": "agent did not acknowledge this recovery request"}})
		return
	}
	forwardExecutionEvents(h.hub, first, events, errs, cancel)
	c.JSON(http.StatusAccepted, gin.H{"task_id": taskID, "conversation_id": task.ConversationId, "status": "processing"})
}
