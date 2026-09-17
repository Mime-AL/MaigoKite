// Package api provides HTTP handler for credential management.
package api

import (
	"net/http"
	"strings"
	"time"

	"github.com/nanamigopher/nanamigopher/gateway/internal/credentialstore"
	agentgrpc "github.com/nanamigopher/nanamigopher/gateway/internal/grpc"

	"github.com/gin-gonic/gin"
)

// CredentialHandler handles API key storage and validation.
type CredentialHandler struct {
	mgr    *credentialstore.Manager
	client *agentgrpc.AgentClient
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

	err := h.mgr.ValidateAndSaveForWorkspace(c.Param("workspaceID"), req.Service, req.APIKey)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "validation failed: " + err.Error()})
		return
	}
	if strings.HasPrefix(req.Service, "model.") {
		if err := h.client.SetChatModelCredential(c.Request.Context(), c.Param("workspaceID"), strings.TrimPrefix(req.Service, "model."), req.APIKey); err != nil {
			grpcError(c, err)
			return
		}
	}
	_ = h.client.RecordAuditEvent(c.Request.Context(), c.Param("workspaceID"), "local-user", "credential.saved", req.Service, "success")

	c.JSON(http.StatusCreated, gin.H{
		"id":        req.Service,
		"service":   req.Service,
		"status":    "saved",
		"validated": false,
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
	engines := []string{"model.openai", "model.anthropic", "model.openai_compatible", "tavily", "google"}
	var statuses []EngineStatus

	for _, engine := range engines {
		key, err := h.mgr.GetForWorkspace(c.Param("workspaceID"), engine)
		configured := err == nil && key != ""
		var validated *bool
		if configured {
			b := false
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

	err := h.mgr.ValidateAndSaveForWorkspace(c.Param("workspaceID"), service, req.APIKey)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "validation failed: " + err.Error()})
		return
	}
	if strings.HasPrefix(service, "model.") {
		if err := h.client.SetChatModelCredential(c.Request.Context(), c.Param("workspaceID"), strings.TrimPrefix(service, "model."), req.APIKey); err != nil {
			grpcError(c, err)
			return
		}
	}
	_ = h.client.RecordAuditEvent(c.Request.Context(), c.Param("workspaceID"), "local-user", "credential.updated", service, "success")

	c.JSON(http.StatusOK, gin.H{
		"id":         service,
		"updated_at": time.Now().UTC().Format(time.RFC3339),
	})
}

// Delete removes a credential entry.
func (h *CredentialHandler) Delete(c *gin.Context) {
	service := c.Param("id")
	err := h.mgr.DeleteForWorkspace(c.Param("workspaceID"), service)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "delete failed: " + err.Error()})
		return
	}
	if strings.HasPrefix(service, "model.") {
		if err := h.client.SetChatModelCredential(c.Request.Context(), c.Param("workspaceID"), strings.TrimPrefix(service, "model."), ""); err != nil {
			grpcError(c, err)
			return
		}
	}
	_ = h.client.RecordAuditEvent(c.Request.Context(), c.Param("workspaceID"), "local-user", "credential.deleted", service, "success")
	c.Status(http.StatusNoContent)
}
