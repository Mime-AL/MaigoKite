package api

import (
	"context"
	"encoding/json"
	"github.com/gin-gonic/gin"
	"github.com/nanamigopher/nanamigopher/gateway/internal/credentialstore"
	agentgrpc "github.com/nanamigopher/nanamigopher/gateway/internal/grpc"
	ws "github.com/nanamigopher/nanamigopher/gateway/internal/websocket"
	agentv1 "github.com/nanamigopher/nanamigopher/gateway/pkg/proto/agent/v1"
	"net/http"
	"time"
)

type MessageHandler struct {
	client *agentgrpc.AgentClient
	hub    *ws.Hub
	mgr    *credentialstore.Manager
}
type SendRequest struct {
	Content     string       `json:"content" binding:"required,max=10000"`
	Attachments []Attachment `json:"attachments"`
}
type Attachment struct {
	Type string `json:"type" binding:"omitempty,oneof=file image url"`
	Path string `json:"path"`
	URL  string `json:"url"`
}

func (h *MessageHandler) Send(c *gin.Context) {
	var req SendRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "VALIDATION", "message": err.Error()}})
		return
	}
	attachments := make([]*agentv1.Attachment, 0, len(req.Attachments))
	for _, a := range req.Attachments {
		attachments = append(attachments, &agentv1.Attachment{Type: a.Type, Path: a.Path, Url: a.URL})
	}
	conversationID := c.Param("conversationID")
	conversation, err := h.client.GetConversation(c.Request.Context(), &agentv1.ConversationRequest{
		WorkspaceId: c.Param("workspaceID"), ConversationId: conversationID,
	})
	if err != nil {
		grpcError(c, err)
		return
	}
	catalog, err := h.client.ListChatModels(c.Request.Context(), c.Param("workspaceID"))
	if err != nil {
		grpcError(c, err)
		return
	}
	selectedID := conversation.ModelId
	if selectedID == "" {
		selectedID = catalog.DefaultModelId
	}
	for _, settings := range catalog.Models {
		if settings.Id != selectedID {
			continue
		}
		apiKey, keyErr := h.mgr.GetModelProfileKeyForWorkspace(c.Param("workspaceID"), settings.Id)
		if keyErr != nil && settings.Id == "model_default" {
			apiKey, _ = h.mgr.GetModelKeyForWorkspace(c.Param("workspaceID"), settings.Provider)
		}
		if err := h.client.SetChatModelProfileCredential(c.Request.Context(), c.Param("workspaceID"), settings.Id, settings.Provider, apiKey); err != nil {
			grpcError(c, err)
			return
		}
		break
	}
	// Agent Core keeps secrets in memory only. Re-sync search credentials before
	// every task so a Core restart does not silently fall back to another provider.
	for _, service := range []string{"tavily", "google"} {
		apiKey, _ := h.mgr.GetSearchKeyForWorkspace(c.Param("workspaceID"), service)
		if err := h.client.SetToolCredential(c.Request.Context(), c.Param("workspaceID"), service, apiKey); err != nil {
			grpcError(c, err)
			return
		}
	}
	streamContext, cancel := context.WithTimeout(context.Background(), 10*time.Minute)
	events, errs := h.client.ProcessMessage(streamContext, &agentv1.ProcessMessageRequest{WorkspaceId: c.Param("workspaceID"), ConversationId: conversationID, Content: req.Content, Attachments: attachments, PrincipalId: "local-user"})
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
			payload, _ = json.Marshal(gin.H{"content": event.Content, "message": event.Message, "code": event.Code, "retryable": event.Retryable})
		}
		h.hub.BroadcastEvent(conversationID, event.TaskId, event.Type, payload)
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
	c.JSON(http.StatusAccepted, gin.H{"task_id": first.TaskId, "conversation_id": conversationID, "status": "processing"})
}
func (h *MessageHandler) Stream(c *gin.Context) {
	conversationID := c.Query("conversation_id")
	if conversationID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "VALIDATION", "message": "conversation_id is required"}})
		return
	}
	if _, err := h.client.GetConversation(c.Request.Context(), &agentv1.ConversationRequest{
		WorkspaceId: c.Param("workspaceID"), ConversationId: conversationID,
	}); err != nil {
		grpcError(c, err)
		return
	}
	if err := h.hub.ServeWS(c.Writer, c.Request, conversationID); err != nil {
		return
	}
}
