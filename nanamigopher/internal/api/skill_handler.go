// Package api provides HTTP handler for skill management.
package api

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

// SkillHandler handles skill registration, listing, and uninstallation.
type SkillHandler struct{}

// SkillItem represents a registered skill.
type SkillItem struct {
	ID            string `json:"id"`
	Name          string `json:"name"`
	Version       string `json:"version"`
	Description   string `json:"description"`
	Namespace     string `json:"namespace"`
	PermissionLevel int  `json:"permission_level"`
	IsActive      bool   `json:"is_active"`
}

// List returns all registered skills with optional namespace filter.
func (h *SkillHandler) List(c *gin.Context) {
	namespace := c.Query("namespace")
	// TODO: query skill registry
	_ = namespace
	c.JSON(http.StatusOK, gin.H{"skills": []SkillItem{}})
}

// ImportRequest represents a skill import request.
type ImportRequest struct {
	Name string `json:"name"`
	Mode string `json:"mode"` // self_contained, directory
}

// Import adds a new skill from a SKILL.md file or directory.
func (h *SkillHandler) Import(c *gin.Context) {
	var req ImportRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	// TODO: parse SKILL.md and register skill
	c.JSON(http.StatusCreated, gin.H{"id": "skill_placeholder", "name": req.Name, "status": "imported"})
}

// Uninstall removes a skill by ID.
func (h *SkillHandler) Uninstall(c *gin.Context) {
	_ = c.Param("id")
	// TODO: unregister skill
	c.Status(http.StatusNoContent)
}

// Dependencies returns the dependency graph for a skill.
func (h *SkillHandler) Dependencies(c *gin.Context) {
	id := c.Param("id")
	// TODO: resolve skill dependencies
	c.JSON(http.StatusOK, gin.H{"skill_name": id, "dependencies": []interface{}{}})
}
