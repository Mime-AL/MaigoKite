// Package api provides HTTP handler for message operations.
package api

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

// MessageHandler handles sending messages and streaming responses.
type MessageHandler struct{}

// SendRequest represents a message send request.
type SendRequest struct {
	Content     string        `json:"content" binding:"required"`
	Attachments []Attachment  `json:"attachments"`
}

// Attachment represents a message attachment.
type Attachment struct {
	Type string `json:"type"` // file, image, url
	Path string `json:"path"`
	URL  string `json:"url"`
}

// Send forwards a message to the Python Agent via gRPC and initiates streaming.
func (h *MessageHandler) Send(c *gin.Context) {
	_ = c.Param("id")
	var req SendRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	// TODO: call gRPC ProcessMessage and forward to WebSocket hub
	c.JSON(http.StatusAccepted, gin.H{
		"message_id": "msg_placeholder",
		"status":     "processing",
	})
}

// Stream handles WebSocket upgrade for real-time message streaming.
func (h *MessageHandler) Stream(c *gin.Context) {
	sessionID := c.Param("id")
	// TODO: upgrade connection and forward gRPC stream
	_ = sessionID
	c.String(http.StatusNotImplemented, "WebSocket stream not yet implemented")
}
