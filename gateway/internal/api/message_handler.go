package api

import (
	"context"
	"encoding/json"
	"github.com/gin-gonic/gin"
	"maigokite/gateway/internal/credentialstore"
	agentgrpc "maigokite/gateway/internal/grpc"
	ws "maigokite/gateway/internal/websocket"
	agentv1 "maigokite/gateway/pkg/proto/agent/v1"
	"net/http"
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
	if err := prepareExecutionCredentials(c.Request.Context(), h.client, h.mgr, c.Param("workspaceID"), conversationID); err != nil {
		grpcError(c, err)
		return
	}
	// The HTTP request only starts the durable task. Its gRPC stream deliberately
	// outlives the request and ends on completion, explicit cancellation, or process shutdown.
	streamContext, cancel := context.WithCancel(context.Background())
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
		h.hub.BroadcastPersistedEvent(
			conversationID, event.TaskId, event.Type, payload,
			event.EventId, uint64(event.Sequence), event.OccurredAt,
		)
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
