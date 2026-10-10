package api

import (
	"context"
	"crypto/sha256"
	"fmt"
	"github.com/gin-gonic/gin"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
	"maigokite/gateway/internal/credentialstore"
	agentgrpc "maigokite/gateway/internal/grpc"
	ws "maigokite/gateway/internal/websocket"
	agentv1 "maigokite/gateway/pkg/proto/agent/v1"
	"net/http"
	"strings"
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
	key := c.GetHeader("Idempotency-Key")
	if len(key) > 128 || strings.IndexFunc(key, func(r rune) bool { return r < 33 || r > 126 }) >= 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "VALIDATION", "message": "Idempotency-Key must contain at most 128 printable ASCII characters without spaces"}})
		return
	}
	replay := false
	if key != "" {
		// Same scoped identity as Core. Core alone validates the request fingerprint.
		digest := sha256.Sum256([]byte(strings.Join([]string{c.Param("workspaceID"), conversationID, "local-user", key}, "\x00")))
		_, err := h.client.GetTask(c.Request.Context(), c.Param("workspaceID"), fmt.Sprintf("task_%x", digest))
		replay = err == nil
		if err != nil && status.Code(err) != codes.NotFound {
			grpcError(c, err)
			return
		}
	}
	if !replay {
		if err := prepareExecutionCredentials(c.Request.Context(), h.client, h.mgr, c.Param("workspaceID"), conversationID); err != nil {
			grpcError(c, err)
			return
		}
	}
	// The HTTP request only starts the durable task. Its gRPC stream deliberately
	// outlives the request and ends on completion, explicit cancellation, or process shutdown.
	streamContext, cancel := context.WithCancel(context.Background())
	events, errs := h.client.ProcessMessage(streamContext, &agentv1.ProcessMessageRequest{WorkspaceId: c.Param("workspaceID"), ConversationId: conversationID, Content: req.Content, Attachments: attachments, PrincipalId: "local-user", IdempotencyKey: key})
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
	if first.Code == "MESSAGE_REPLAY" {
		cancel()
		c.Header("Idempotency-Replayed", "true")
		c.Data(http.StatusOK, "application/json", []byte(first.PayloadJson))
		return
	}
	if first.Type == "error" {
		cancel()
		c.JSON(http.StatusBadGateway, gin.H{"error": gin.H{"code": first.Code, "message": first.Message}})
		return
	}
	forwardExecutionEvents(h.hub, first, events, errs, cancel)
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
