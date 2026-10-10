package api

import (
	"github.com/gin-gonic/gin"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
	agentgrpc "maigokite/gateway/internal/grpc"
	agentv1 "maigokite/gateway/pkg/proto/agent/v1"
	"net/http"
)

type SessionHandler struct{ client *agentgrpc.AgentClient }

func (h *SessionHandler) Snapshot(c *gin.Context) {
	item, err := h.client.GetConversationSnapshot(c.Request.Context(), &agentv1.ConversationRequest{
		WorkspaceId: c.Param("workspaceID"), ConversationId: c.Param("conversationID"),
	})
	if err != nil {
		grpcError(c, err)
		return
	}
	// Empty protobuf repeated fields are nil in Go; keep the JSON list contract.
	if item.Messages == nil {
		item.Messages = []*agentv1.Message{}
	}
	if item.Tasks == nil {
		item.Tasks = []*agentv1.Task{}
	}
	if item.Approvals == nil {
		item.Approvals = []*agentv1.Approval{}
	}
	if item.Questions == nil {
		item.Questions = []*agentv1.Question{}
	}
	c.JSON(http.StatusOK, gin.H{"messages": item.Messages, "tasks": item.Tasks,
		"approvals": item.Approvals, "questions": item.Questions,
		"last_sequence": item.LastSequence, "truncated": item.Truncated})
}

type CreateRequest struct {
	SubagentModelIDs       []string `json:"subagent_model_ids" binding:"max=32,dive,required,max=100"`
	MaxSubagentCalls       *int32   `json:"max_subagent_calls" binding:"omitempty,min=0,max=32"`
	MaxConcurrentSubagents *int32   `json:"max_concurrent_subagents" binding:"omitempty,min=1,max=8"`
	FolderID               string   `json:"folder_id" binding:"max=200"`
	Title                  string   `json:"title" binding:"max=200"`
	ModelID                string   `json:"model_id" binding:"max=200"`
	PermissionMode         string   `json:"permission_mode" binding:"omitempty,oneof=read_only workspace full_access"`
	ResponseMode           string   `json:"response_mode" binding:"omitempty,oneof=fast balanced thorough"`
}
type UpdateConversationRequest struct {
	SubagentModelIDs       *[]string `json:"subagent_model_ids" binding:"omitempty,max=32,dive,required,max=100"`
	MaxSubagentCalls       *int32    `json:"max_subagent_calls" binding:"omitempty,min=0,max=32"`
	MaxConcurrentSubagents *int32    `json:"max_concurrent_subagents" binding:"omitempty,min=1,max=8"`
	Title                  *string   `json:"title" binding:"omitempty,min=1,max=200"`
	FolderID               *string   `json:"folder_id" binding:"omitempty,max=200"`
	Archived               *bool     `json:"archived"`
	PermissionMode         *string   `json:"permission_mode" binding:"omitempty,oneof=read_only workspace full_access"`
	ModelID                *string   `json:"model_id" binding:"omitempty,max=200"`
	ResponseMode           *string   `json:"response_mode" binding:"omitempty,oneof=fast balanced thorough"`
}

func grpcError(c *gin.Context, err error) {
	code := http.StatusBadGateway
	if status.Code(err) == codes.NotFound {
		code = http.StatusNotFound
	} else if status.Code(err) == codes.InvalidArgument {
		code = http.StatusBadRequest
	} else if status.Code(err) == codes.FailedPrecondition || status.Code(err) == codes.Aborted || status.Code(err) == codes.AlreadyExists {
		code = http.StatusConflict
	} else if status.Code(err) == codes.PermissionDenied {
		code = http.StatusForbidden
	} else if status.Code(err) == codes.Unimplemented {
		code = http.StatusNotImplemented
	}
	c.JSON(code, gin.H{"error": gin.H{"code": status.Code(err).String(), "message": status.Convert(err).Message()}})
}
func (h *SessionHandler) Create(c *gin.Context) {
	var req CreateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "VALIDATION", "message": err.Error()}})
		return
	}
	item, err := h.client.CreateConversation(c.Request.Context(), &agentv1.ConversationRequest{
		WorkspaceId: c.Param("workspaceID"), Title: req.Title, ModelId: req.ModelID,
		PermissionMode: req.PermissionMode, ResponseMode: req.ResponseMode, FolderId: req.FolderID,
		MaxSubagentCalls: req.MaxSubagentCalls, MaxConcurrentSubagents: req.MaxConcurrentSubagents,
		SubagentModelIds: req.SubagentModelIDs,
	})
	if err != nil {
		grpcError(c, err)
		return
	}
	c.JSON(http.StatusCreated, item)
}
func (h *SessionHandler) List(c *gin.Context) {
	items, err := h.client.ListConversations(c.Request.Context(), c.Param("workspaceID"))
	if err != nil {
		grpcError(c, err)
		return
	}
	c.JSON(http.StatusOK, items)
}
func (h *SessionHandler) Get(c *gin.Context) {
	item, err := h.client.GetConversation(c.Request.Context(), &agentv1.ConversationRequest{WorkspaceId: c.Param("workspaceID"), ConversationId: c.Param("conversationID")})
	if err != nil {
		grpcError(c, err)
		return
	}
	c.JSON(http.StatusOK, item)
}
func (h *SessionHandler) Update(c *gin.Context) {
	var req UpdateConversationRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "VALIDATION", "message": err.Error()}})
		return
	}
	if req.PermissionMode == nil && req.ModelID == nil && req.ResponseMode == nil && req.Title == nil && req.FolderID == nil && req.Archived == nil && req.MaxSubagentCalls == nil && req.MaxConcurrentSubagents == nil && req.SubagentModelIDs == nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "VALIDATION", "message": "at least one conversation setting is required"}})
		return
	}
	var selectedModels *agentv1.ModelIdList
	if req.SubagentModelIDs != nil {
		selectedModels = &agentv1.ModelIdList{ModelIds: *req.SubagentModelIDs}
	}
	item, err := h.client.UpdateConversationSettings(c.Request.Context(), &agentv1.ConversationSettingsRequest{
		WorkspaceId: c.Param("workspaceID"), ConversationId: c.Param("conversationID"),
		PermissionMode: req.PermissionMode, ModelId: req.ModelID, ResponseMode: req.ResponseMode,
		Title: req.Title, FolderId: req.FolderID, Archived: req.Archived,
		SubagentModels:   selectedModels,
		MaxSubagentCalls: req.MaxSubagentCalls, MaxConcurrentSubagents: req.MaxConcurrentSubagents,
	})
	if err != nil {
		grpcError(c, err)
		return
	}
	c.JSON(http.StatusOK, item)
}
func (h *SessionHandler) Delete(c *gin.Context) {
	err := h.client.DeleteConversation(c.Request.Context(), &agentv1.ConversationRequest{WorkspaceId: c.Param("workspaceID"), ConversationId: c.Param("conversationID")})
	if err != nil {
		grpcError(c, err)
		return
	}
	c.Status(http.StatusNoContent)
}
func (h *SessionHandler) Messages(c *gin.Context) {
	items, err := h.client.ListMessages(c.Request.Context(), &agentv1.ConversationRequest{WorkspaceId: c.Param("workspaceID"), ConversationId: c.Param("conversationID")})
	if err != nil {
		grpcError(c, err)
		return
	}
	c.JSON(http.StatusOK, items)
}
