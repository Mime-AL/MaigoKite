// Package api provides HTTP handler for approval and takeover management.
package api

import (
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
)

// ApprovalHandler handles human-in-the-loop approval requests.
type ApprovalHandler struct{}

// ApprovalRequest represents a user request to approve an agent action.
type ApprovalRequest struct {
	Action        string                 `json:"action" binding:"required"`
	Preview       map[string]interface{} `json:"preview"`
	TimeoutSeconds int                   `json:"timeout_seconds"`
}

// Create submits a new approval request and returns a request ID.
func (h *ApprovalHandler) Create(c *gin.Context) {
	var req ApprovalRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	// TODO: persist approval request and notify frontend via WebSocket
	c.JSON(http.StatusCreated, gin.H{
		"request_id":  "req_placeholder",
		"status":      "pending",
		"expires_at":  time.Now().Add(time.Duration(req.TimeoutSeconds) * time.Second),
	})
}

// Get returns the details of an approval request.
func (h *ApprovalHandler) Get(c *gin.Context) {
	id := c.Param("id")
	// TODO: query approval store
	_ = id
	c.JSON(http.StatusOK, gin.H{"request_id": id, "status": "pending"})
}

// DecisionRequest represents the user's approval decision.
type DecisionRequest struct {
	Decision       string                 `json:"decision" binding:"required"` // approve, reject
	SelectedJobs   []interface{}          `json:"selected_jobs,omitempty"`
	ModifiedMessage *string               `json:"modified_message,omitempty"`
}

// Decide records the user's approval decision.
func (h *ApprovalHandler) Decide(c *gin.Context) {
	id := c.Param("id")
	var req DecisionRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	// TODO: record decision and notify Python Agent via gRPC
	_ = id
	_ = req
	c.JSON(http.StatusOK, gin.H{
		"request_id":  id,
		"decision":    req.Decision,
		"processed_at": "now",
	})
}

// ApprovalRecord is a single entry in the approval history.
type ApprovalRecord struct {
	RequestID  string `json:"request_id"`
	Action     string `json:"action"`
	Decision   string `json:"decision"`
	ProcessedAt string `json:"processed_at"`
}

// History returns past approval decisions.
func (h *ApprovalHandler) History(c *gin.Context) {
	page := c.DefaultQuery("page", "1")
	perPage := c.DefaultQuery("per_page", "20")
	// TODO: query approval history store
	_ = page
	_ = perPage
	c.JSON(http.StatusOK, gin.H{
		"approvals": []ApprovalRecord{},
		"total":     0,
		"page":      page,
	})
}
