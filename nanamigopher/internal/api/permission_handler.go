// Package api provides HTTP handler for permission management.
package api

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

// PermissionHandler handles permission mode configuration and switching.
type PermissionHandler struct{}

// ModeOption represents an available permission mode.
type ModeOption struct {
	Name       string `json:"name"`
	IsDefault  bool   `json:"is_default"`
}

// Get returns the current permission configuration.
func (h *PermissionHandler) Get(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"current_mode": "manual",
		"modes": []ModeOption{
			{Name: "manual", IsDefault: true},
			{Name: "accept_edits", IsDefault: false},
			{Name: "plan", IsDefault: false},
			{Name: "auto", IsDefault: false},
		},
		"circuit_breaker": gin.H{
			"enabled": true,
			"blocked_patterns": []string{"rm -rf /", "dd if="},
		},
	})
}

// PermissionUpdateRequest represents a permission configuration update.
type PermissionUpdateRequest struct {
	DefaultMode     string   `json:"default_mode"`
	CircuitBreaker  *CBConfig `json:"circuit_breaker"`
}

// CBConfig holds circuit breaker settings.
type CBConfig struct {
	Enabled          bool     `json:"enabled"`
	BlockedPatterns  []string `json:"blocked_patterns"`
}

// Update modifies the permission configuration.
func (h *PermissionHandler) Update(c *gin.Context) {
	var req PermissionUpdateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	// TODO: persist new permission config
	c.JSON(http.StatusOK, gin.H{"updated_at": "now"})
}

// SwitchModeRequest represents a mode change request.
type SwitchModeRequest struct {
	Mode string `json:"mode" binding:"required"`
}

// SwitchMode changes the active permission mode.
func (h *PermissionHandler) SwitchMode(c *gin.Context) {
	var req SwitchModeRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	// TODO: update session permission mode
	c.JSON(http.StatusOK, gin.H{
		"previous_mode": "manual",
		"current_mode":  req.Mode,
		"switched_at":   "now",
	})
}
