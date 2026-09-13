// Package api provides HTTP routing and handler definitions for the gateway.
package api

import (
	"nanamigopher/internal/credentialstore"
	"nanamigopher/internal/observability"

	"github.com/gin-gonic/gin"
)

// Router manages all HTTP routes for the gateway.
type Router struct {
	engine     *gin.Engine
	cfg        *config.Config
	obs        observability.ConsoleObserver
	credMgr    *credentialstore.Manager
	session    *SessionHandler
	message    *MessageHandler
	memory     *MemoryHandler
	skill      *SkillHandler
	permission *PermissionHandler
	credential *CredentialHandler
	inspector  *InspectorHandler
	approval   *ApprovalHandler
}

// NewRouter creates and configures the Gin engine with all route handlers.
func NewRouter(cfg *config.Config, obs observability.ConsoleObserver, credMgr *credentialstore.Manager) *gin.Engine {
	gin.SetMode(gin.ReleaseMode)
	engine := gin.Default()

	r := &Router{
		engine:     engine,
		cfg:        cfg,
		obs:        obs,
		credMgr:    credMgr,
		session:    &SessionHandler{},
		message:    &MessageHandler{},
		memory:     &MemoryHandler{},
		skill:      &SkillHandler{},
		permission: &PermissionHandler{},
		credential: &CredentialHandler{mgr: credMgr},
		inspector:  &InspectorHandler{},
		approval:   &ApprovalHandler{},
	}

	r.registerRoutes()
	return engine
}

// registerRoutes sets up all API v1 endpoints.
func (r *Router) registerRoutes() {
	v1 := r.engine.Group("/api/v1")

	// Session management
	sessions := v1.Group("/sessions")
	{
		sessions.POST("", r.session.Create)
		sessions.GET("", r.session.List)
		sessions.GET("/:id", r.session.Get)
		sessions.DELETE("/:id", r.session.Delete)
		sessions.POST("/:id/switch", r.session.Switch)
		sessions.POST("/:id/messages", r.message.Send)
		sessions.GET("/:id/stream", r.message.Stream)
	}

	// Memory management
	memories := v1.Group("/memories")
	{
		memories.GET("", r.memory.List)
		memories.POST("/search", r.memory.Search)
		memories.PUT("/:id", r.memory.Update)
		memories.DELETE("/batch", r.memory.BatchDelete)
	}

	// Skill management
	skills := v1.Group("/skills")
	{
		skills.GET("", r.skill.List)
		skills.POST("/import", r.skill.Import)
		skills.DELETE("/:id", r.skill.Uninstall)
		skills.GET("/:id/deps", r.skill.Dependencies)
	}

	// Permission management
	perms := v1.Group("/permissions")
	{
		perms.GET("", r.permission.Get)
		perms.PUT("", r.permission.Update)
		perms.POST("/mode", r.permission.SwitchMode)
	}

	// Credential management
	creds := v1.Group("/credentials")
	{
		creds.POST("/search/save", r.credential.Save)
		creds.GET("/search/status", r.credential.Status)
		creds.PUT("/search/:id", r.credential.Update)
		creds.DELETE("/search/:id", r.credential.Delete)
	}

	// Inspector monitoring
	inspector := v1.Group("/inspector")
	{
		inspector.GET("/cards", r.inspector.Cards)
		inspector.GET("/sessions/:id/timeline", r.inspector.Timeline)
		inspector.GET("/history", r.inspector.History)
		inspector.PUT("/settings", r.inspector.UpdateSettings)
	}

	// Approval management
	approvals := v1.Group("/approvals")
	{
		approvals.POST("", r.approval.Create)
		approvals.GET("/:id", r.approval.Get)
		approvals.PUT("/:id/decision", r.approval.Decide)
		approvals.GET("/history", r.approval.History)
	}
}
