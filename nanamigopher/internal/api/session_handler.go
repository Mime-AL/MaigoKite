// Package api provides HTTP handler for session management.
package api

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

// SessionHandler handles session lifecycle operations.
type SessionHandler struct{}

// CreateRequest represents a request to create a new session.
type CreateRequest struct {
	Title         string `json:"title"`
	ModelID       string `json:"model_id"`
	PermissionMode string `json:"permission_mode"`
}

// Create creates a new session via gRPC call to Python Agent.
func (h *SessionHandler) Create(c *gin.Context) {
	var req CreateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	// TODO: forward to gRPC client
	c.JSON(http.StatusCreated, gin.H{"id": "sess_placeholder", "title": req.Title})
}

// List lists all sessions.
func (h *SessionHandler) List(c *gin.Context) {
	// TODO: query gRPC client
	c.JSON(http.StatusOK, gin.H{"sessions": []interface{}{}})
}

// Get retrieves a single session by ID.
func (h *SessionHandler) Get(c *gin.Context) {
	id := c.Param("id")
	// TODO: query gRPC client
	c.JSON(http.StatusOK, gin.H{"id": id})
}

// Delete removes a session.
func (h *SessionHandler) Delete(c *gin.Context) {
	_ = c.Param("id")
	// TODO: forward to gRPC client
	c.Status(http.StatusNoContent)
}

// SwitchRequest represents a request to switch sessions.
type SwitchRequest struct {
	SessionID string `uri:"id" binding:"required"`
}

// Switch activates a session as the current one.
func (h *SessionHandler) Switch(c *gin.Context) {
	id := c.Param("id")
	// TODO: forward to gRPC client
	c.JSON(http.StatusOK, gin.H{"id": id})
}
