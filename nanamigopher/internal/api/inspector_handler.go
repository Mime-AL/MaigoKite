// Package api provides HTTP handler for Inspector monitoring.
package api

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

// InspectorHandler handles real-time monitoring of agent execution.
type InspectorHandler struct{}

// Card represents an activity card in the inspector dashboard.
type Card struct {
	SessionID          string `json:"session_id"`
	Title              string `json:"title"`
	Status             string `json:"status"` // running, completed, failed, paused
	RunningDurationSec int    `json:"running_duration_sec,omitempty"`
	TotalDurationSec   int    `json:"total_duration_sec,omitempty"`
	CurrentStep        string `json:"current_step,omitempty"`
	TokenCount         int    `json:"token_count"`
	ToolCallCount      int    `json:"tool_call_count"`
	Error              string `json:"error,omitempty"`
	RetryCount         int    `json:"retry_count,omitempty"`
	SubAgentCount      int    `json:"subagent_count"`
	SubAgentRunning    int    `json:"subagent_running"`
	SubAgentCompleted  int    `json:"subagent_completed"`
}

// Cards returns all inspector activity cards.
func (h *InspectorHandler) Cards(c *gin.Context) {
	// TODO: aggregate from WebSocket hub state
	c.JSON(http.StatusOK, gin.H{"cards": []Card{}})
}

// TimelineNode represents a node in the execution timeline.
type TimelineNode struct {
	NodeID    string          `json:"node_id"`
	NodeType  string          `json:"node_type"` // task, tool, model, event, error, subagent
	Title     string          `json:"title"`
	Status    string          `json:"status"`
	Timestamp string          `json:"timestamp"`
	DurationMs *int64         `json:"duration_ms,omitempty"`
	Details   map[string]interface{} `json:"details,omitempty"`
	Children  []TimelineNode `json:"children,omitempty"`
}

// Timeline returns the execution timeline for a session.
func (h *InspectorHandler) Timeline(c *gin.Context) {
	sessionID := c.Param("id")
	dimensions := c.QueryArray("dimensions")
	// TODO: retrieve from inspector state
	_ = sessionID
	_ = dimensions
	c.JSON(http.StatusOK, gin.H{
		"session_id": sessionID,
		"nodes":      []TimelineNode{},
	})
}

// HistoryResponse contains completed inspector records.
type HistoryResponse struct {
	SessionID    string        `json:"session_id"`
	CompletedAt  string        `json:"completed_at"`
	Nodes        []TimelineNode `json:"nodes"`
	Summary      HistorySummary `json:"summary"`
}

// HistorySummary is a condensed view of a completed session.
type HistorySummary struct {
	TotalDurationSec int `json:"total_duration_sec"`
	TokenCount       int `json:"token_count"`
	ToolCallCount    int `json:"tool_call_count"`
	ErrorCount       int `json:"error_count"`
	SubAgentCount    int `json:"subagent_count"`
}

// History returns historical inspector records.
func (h *InspectorHandler) History(c *gin.Context) {
	sessionID := c.Query("session_id")
	// TODO: query history store
	_ = sessionID
	c.JSON(http.StatusOK, HistoryResponse{})
}

// SettingsRequest represents inspector settings update.
type SettingsRequest struct {
	SaveHistory bool `json:"save_history"`
}

// UpdateSettings toggles inspector history recording.
func (h *InspectorHandler) UpdateSettings(c *gin.Context) {
	var req SettingsRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	// TODO: persist settings
	c.JSON(http.StatusOK, gin.H{"save_history": req.SaveHistory, "updated_at": "now"})
}
