package api

import (
	"context"
	"encoding/json"
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
	agentv1 "github.com/nanamigopher/nanamigopher/gateway/pkg/proto/agent/v1"
)

type taskService interface {
	GetTask(context.Context, string, string) (*agentv1.Task, error)
	ListTasks(context.Context, string, string, int32) (*agentv1.TaskList, error)
	CancelTask(context.Context, string, string) (*agentv1.Task, error)
	ListTaskEvents(context.Context, string, string, int64, int32) (*agentv1.TaskEventList, error)
}

type skillService interface {
	ListSkills(context.Context, string) (*agentv1.SkillList, error)
}

type TaskHandler struct{ client taskService }

func taskValue(item *agentv1.Task) gin.H {
	return gin.H{
		"id": item.Id, "workspace_id": item.WorkspaceId,
		"conversation_id": item.ConversationId, "title": item.Title,
		"status": item.Status, "input_text": item.InputText,
		"last_error": item.LastError, "version": item.Version,
		"created_at": item.CreatedAt, "updated_at": item.UpdatedAt,
	}
}

func (h *TaskHandler) List(c *gin.Context) {
	items, err := h.client.ListTasks(
		c.Request.Context(), c.Param("workspaceID"), c.Query("conversation_id"), 200,
	)
	if err != nil {
		grpcError(c, err)
		return
	}
	result := make([]gin.H, 0, len(items.Tasks))
	for _, item := range items.Tasks {
		result = append(result, taskValue(item))
	}
	c.JSON(http.StatusOK, gin.H{"tasks": result})
}

func (h *TaskHandler) Get(c *gin.Context) {
	item, err := h.client.GetTask(c.Request.Context(), c.Param("workspaceID"), c.Param("taskID"))
	if err != nil {
		grpcError(c, err)
		return
	}
	c.JSON(http.StatusOK, taskValue(item))
}

func (h *TaskHandler) Cancel(c *gin.Context) {
	item, err := h.client.CancelTask(c.Request.Context(), c.Param("workspaceID"), c.Param("taskID"))
	if err != nil {
		grpcError(c, err)
		return
	}
	c.JSON(http.StatusOK, taskValue(item))
}

func (h *TaskHandler) Events(c *gin.Context) {
	after, err := strconv.ParseInt(c.DefaultQuery("after", "0"), 10, 64)
	if err != nil || after < 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "VALIDATION", "message": "after must be a non-negative integer"}})
		return
	}
	items, err := h.client.ListTaskEvents(
		c.Request.Context(), c.Param("workspaceID"), c.Param("conversationID"), after, 1000,
	)
	if err != nil {
		grpcError(c, err)
		return
	}
	result := make([]gin.H, 0, len(items.Events))
	for _, item := range items.Events {
		var payload map[string]any
		if err := json.Unmarshal([]byte(item.PayloadJson), &payload); err != nil {
			payload = map[string]any{}
		}
		result = append(result, gin.H{
			"schema_version": 1, "event_id": item.Id, "sequence": item.Sequence,
			"type": item.EventType, "occurred_at": item.OccurredAt,
			"conversation_id": item.ConversationId, "task_id": item.TaskId,
			"payload": payload,
		})
	}
	c.JSON(http.StatusOK, gin.H{"events": result})
}

type SkillHandler struct{ client skillService }

func (h *SkillHandler) List(c *gin.Context) {
	items, err := h.client.ListSkills(c.Request.Context(), c.Param("workspaceID"))
	if err != nil {
		grpcError(c, err)
		return
	}
	result := make([]gin.H, 0, len(items.Skills))
	for _, item := range items.Skills {
		var parameters map[string]any
		if err := json.Unmarshal([]byte(item.ParametersSchemaJson), &parameters); err != nil {
			parameters = map[string]any{}
		}
		result = append(result, gin.H{
			"name": item.Name, "version": item.Version, "description": item.Description,
			"kind": item.Kind, "source_path": item.SourcePath,
			"parameters_schema": parameters,
		})
	}
	c.JSON(http.StatusOK, gin.H{"skills": result})
}
