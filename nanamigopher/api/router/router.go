// Package router provides router type aliases for external references.
package router

import (
	"github.com/gin-gonic/gin"
	"nanamigopher/internal/api"
	"nanamigopher/internal/config"
	"nanamigopher/internal/observability"
)

// NewRouter creates a Gin router with all API routes registered.
func NewRouter(cfg *config.Config, obs observability.ConsoleObserver) *gin.Engine {
	return api.NewRouter(cfg, obs)
}
