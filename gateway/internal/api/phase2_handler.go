package api

import (
	"context"
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
	agentv1 "maigokite/gateway/pkg/proto/agent/v1"
)

type memoryService interface {
	ListMemories(context.Context, string, string, string, int32) (*agentv1.MemoryList, error)
	UpsertMemory(context.Context, string, string, *agentv1.Memory) (*agentv1.Memory, error)
	DeleteMemory(context.Context, string, string, string) error
}

type dataSummaryService interface {
	GetWorkspaceDataSummary(context.Context, string) (*agentv1.WorkspaceDataSummary, error)
}

type mcpRuntimeService interface {
	ListMCPServers(context.Context, string) (*agentv1.MCPServerList, error)
}

type MemoryHandler struct{ client memoryService }

type memoryInput struct {
	Category   string   `json:"category" binding:"required,max=32"`
	Content    string   `json:"content" binding:"required,max=4000"`
	Confidence *float64 `json:"confidence" binding:"omitempty,gte=0,lte=1"`
}

type memoryResponse struct {
	ID            string  `json:"id"`
	WorkspaceID   string  `json:"workspace_id"`
	SubjectUserID string  `json:"subject_user_id"`
	Category      string  `json:"category"`
	Content       string  `json:"content"`
	SourceType    string  `json:"source_type"`
	SourceID      string  `json:"source_id"`
	Confidence    float64 `json:"confidence"`
	CreatedAt     string  `json:"created_at"`
	UpdatedAt     string  `json:"updated_at"`
}

func memoryValue(item *agentv1.Memory) memoryResponse {
	return memoryResponse{
		ID: item.Id, WorkspaceID: item.WorkspaceId, SubjectUserID: item.SubjectUserId,
		Category: item.Category, Content: item.Content, SourceType: item.SourceType,
		SourceID: item.SourceId, Confidence: item.Confidence,
		CreatedAt: item.CreatedAt, UpdatedAt: item.UpdatedAt,
	}
}

func (h *MemoryHandler) List(c *gin.Context) {
	query := strings.TrimSpace(c.Query("q"))
	if len(query) > 200 {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "VALIDATION", "message": "query must not exceed 200 characters"}})
		return
	}
	items, err := h.client.ListMemories(
		c.Request.Context(), c.Param("workspaceID"), c.GetString("principal_id"), query, 200,
	)
	if err != nil {
		grpcError(c, err)
		return
	}
	result := make([]memoryResponse, 0, len(items.Memories))
	for _, item := range items.Memories {
		result = append(result, memoryValue(item))
	}
	c.JSON(http.StatusOK, gin.H{"memories": result})
}

func (h *MemoryHandler) Create(c *gin.Context) { h.upsert(c, "") }

func (h *MemoryHandler) Update(c *gin.Context) { h.upsert(c, c.Param("memoryID")) }

func (h *MemoryHandler) upsert(c *gin.Context, memoryID string) {
	var input memoryInput
	if err := c.ShouldBindJSON(&input); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "VALIDATION", "message": err.Error()}})
		return
	}
	confidence := 1.0
	if input.Confidence != nil {
		confidence = *input.Confidence
	}
	item, err := h.client.UpsertMemory(
		c.Request.Context(), c.Param("workspaceID"), c.GetString("principal_id"),
		&agentv1.Memory{Id: memoryID, Category: input.Category, Content: input.Content, Confidence: confidence},
	)
	if err != nil {
		grpcError(c, err)
		return
	}
	status := http.StatusOK
	if memoryID == "" {
		status = http.StatusCreated
	}
	c.JSON(status, memoryValue(item))
}

func (h *MemoryHandler) Delete(c *gin.Context) {
	if err := h.client.DeleteMemory(
		c.Request.Context(), c.Param("workspaceID"), c.GetString("principal_id"), c.Param("memoryID"),
	); err != nil {
		grpcError(c, err)
		return
	}
	c.Status(http.StatusNoContent)
}

type DataHandler struct{ client dataSummaryService }

func (h *DataHandler) Summary(c *gin.Context) {
	item, err := h.client.GetWorkspaceDataSummary(c.Request.Context(), c.Param("workspaceID"))
	if err != nil {
		grpcError(c, err)
		return
	}
	c.JSON(http.StatusOK, gin.H{
		"storage_backend":    item.StorageBackend,
		"conversation_count": item.ConversationCount,
		"message_count":      item.MessageCount,
		"memory_count":       item.MemoryCount,
		"task_count":         item.TaskCount,
		"audit_event_count":  item.AuditEventCount,
	})
}

type MCPRuntimeHandler struct{ client mcpRuntimeService }

func (h *MCPRuntimeHandler) List(c *gin.Context) {
	items, err := h.client.ListMCPServers(c.Request.Context(), c.Param("workspaceID"))
	if err != nil {
		grpcError(c, err)
		return
	}
	servers := make([]gin.H, 0, len(items.Servers))
	for _, item := range items.Servers {
		servers = append(servers, gin.H{
			"namespace": item.Namespace, "status": item.Status,
			"transport": item.Transport, "tool_names": item.ToolNames,
		})
	}
	c.JSON(http.StatusOK, gin.H{"servers": servers})
}
