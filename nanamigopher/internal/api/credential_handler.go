// Package api provides HTTP handler for credential management.
package api

import (
	"net/http"
	"time"

	"nanamigopher/internal/credentialstore"

	"github.com/gin-gonic/gin"
)

// CredentialHandler handles API key storage and validation.
type CredentialHandler struct {
	mgr *credentialstore.Manager
}

// SaveRequest represents a credential save request.
type SaveRequest struct {
	Service string `json:"service" binding:"required"`
	APIKey  string `json:"api_key" binding:"required"`
}

// Save validates and stores an API key in the platform keychain.
func (h *CredentialHandler) Save(c *gin.Context) {
	var req SaveRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	err := h.mgr.ValidateAndSave(req.Service, req.APIKey)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "validation failed: " + err.Error()})
		return
	}

	c.JSON(http.StatusCreated, gin.H{
		"id":        req.Service,
		"service":   req.Service,
		"status":    "saved",
		"validated": true,
	})
}

// StatusResponse represents the configuration status of credential engines.
type StatusResponse struct {
	Engines []EngineStatus `json:"engines"`
}

// EngineStatus holds the configured/validated state for a service.
type EngineStatus struct {
	Name       string `json:"name"`
	Configured bool   `json:"configured"`
	Validated  *bool  `json:"validated,omitempty"`
}

// Status returns the configuration status for search engine credentials.
func (h *CredentialHandler) Status(c *gin.Context) {
	engines := []string{"tavily", "duckduckgo", "google"}
	var statuses []EngineStatus

	for _, engine := range engines {
		key, err := h.mgr.GetSearchKey(engine)
		configured := err == nil && key != ""
		var validated *bool
		if configured {
			b := true
			validated = &b
		}
		statuses = append(statuses, EngineStatus{
			Name:       engine,
			Configured: configured,
			Validated:  validated,
		})
	}

	c.JSON(http.StatusOK, StatusResponse{Engines: statuses})
}

// CredentialUpdateRequest represents a credential update request.
type CredentialUpdateRequest struct {
	APIKey string `json:"api_key" binding:"required"`
}

// Update modifies an existing credential entry.
func (h *CredentialHandler) Update(c *gin.Context) {
	service := c.Param("id")
	var req CredentialUpdateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	err := h.mgr.ValidateAndSave(service, req.APIKey)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "validation failed: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"id":        service,
		"updated_at": time.Now().UTC().Format(time.RFC3339),
	})
}

// Delete removes a credential entry.
func (h *CredentialHandler) Delete(c *gin.Context) {
	service := c.Param("id")
	err := h.mgr.Delete("search", service)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "delete failed: " + err.Error()})
		return
	}
	c.Status(http.StatusNoContent)
}
