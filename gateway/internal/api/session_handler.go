package api

import (
	"github.com/gin-gonic/gin"
	agentgrpc "github.com/nanamigopher/nanamigopher/gateway/internal/grpc"
	agentv1 "github.com/nanamigopher/nanamigopher/gateway/pkg/proto/agent/v1"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
	"net/http"
)

type SessionHandler struct{ client *agentgrpc.AgentClient }
type CreateRequest struct {
	Title          string `json:"title" binding:"max=200"`
	ModelID        string `json:"model_id" binding:"max=200"`
	PermissionMode string `json:"permission_mode" binding:"omitempty,oneof=read_only workspace full_access"`
	ResponseMode   string `json:"response_mode" binding:"omitempty,oneof=fast balanced thorough"`
}
type UpdateConversationRequest struct {
	PermissionMode *string `json:"permission_mode" binding:"omitempty,oneof=read_only workspace full_access"`
	ModelID        *string `json:"model_id" binding:"omitempty,max=200"`
	ResponseMode   *string `json:"response_mode" binding:"omitempty,oneof=fast balanced thorough"`
}

func grpcError(c *gin.Context, err error) {
	code := http.StatusBadGateway
	if status.Code(err) == codes.NotFound {
		code = http.StatusNotFound
	} else if status.Code(err) == codes.InvalidArgument {
		code = http.StatusBadRequest
	}
	c.JSON(code, gin.H{"error": gin.H{"code": status.Code(err).String(), "message": status.Convert(err).Message()}})
}
func (h *SessionHandler) Create(c *gin.Context) {
	var req CreateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "VALIDATION", "message": err.Error()}})
		return
	}
	item, err := h.client.CreateConversation(c.Request.Context(), &agentv1.ConversationRequest{WorkspaceId: c.Param("workspaceID"), Title: req.Title, ModelId: req.ModelID, PermissionMode: req.PermissionMode, ResponseMode: req.ResponseMode})
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
	if req.PermissionMode == nil && req.ModelID == nil && req.ResponseMode == nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "VALIDATION", "message": "at least one conversation setting is required"}})
		return
	}
	item, err := h.client.UpdateConversationSettings(c.Request.Context(), &agentv1.ConversationSettingsRequest{
		WorkspaceId: c.Param("workspaceID"), ConversationId: c.Param("conversationID"),
		PermissionMode: req.PermissionMode, ModelId: req.ModelID, ResponseMode: req.ResponseMode,
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
