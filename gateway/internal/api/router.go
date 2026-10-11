package api

import (
	"github.com/gin-gonic/gin"
	"maigokite/gateway/internal/config"
	"maigokite/gateway/internal/credentialstore"
	agentgrpc "maigokite/gateway/internal/grpc"
	"maigokite/gateway/internal/observability"
	ws "maigokite/gateway/internal/websocket"
	"net"
	"net/http"
	"strings"
)

type Router struct {
	engine *gin.Engine
	cfg    *config.Config
	obs    observability.ConsoleObserver
	client *agentgrpc.AgentClient
	hub    *ws.Hub
}

func NewRouter(cfg *config.Config, obs observability.ConsoleObserver, client *agentgrpc.AgentClient) *gin.Engine {
	if cfg.App.Env == "development" {
		gin.SetMode(gin.DebugMode)
	} else {
		gin.SetMode(gin.ReleaseMode)
	}
	engine := gin.New()
	engine.Use(gin.Recovery())
	engine.Use(localOriginBoundary())
	r := &Router{engine: engine, cfg: cfg, obs: obs, client: client, hub: ws.NewHub()}
	r.routes()
	return engine
}

func localOriginBoundary() gin.HandlerFunc {
	return func(c *gin.Context) {
		origin := c.GetHeader("Origin")
		remoteHost, _, _ := net.SplitHostPort(c.Request.RemoteAddr)
		loopback := net.ParseIP(remoteHost) != nil && net.ParseIP(remoteHost).IsLoopback()
		trusted := origin == "" || (loopback && (origin == "null" || strings.HasPrefix(origin, "http://localhost:") || strings.HasPrefix(origin, "http://127.0.0.1:")))
		if !trusted {
			c.AbortWithStatusJSON(http.StatusForbidden, gin.H{"error": gin.H{"code": "ORIGIN_DENIED", "message": "origin is not allowed"}})
			return
		}
		if origin != "" {
			c.Header("Access-Control-Allow-Origin", origin)
			c.Header("Vary", "Origin")
			c.Header("Access-Control-Allow-Headers", "Content-Type, Idempotency-Key")
			c.Header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
		}
		if c.Request.Method == http.MethodOptions {
			c.AbortWithStatus(http.StatusNoContent)
			return
		}
		c.Next()
	}
}
func (r *Router) routes() {
	r.engine.GET("/health", func(c *gin.Context) {
		health, err := r.client.Health(c.Request.Context())
		if err != nil {
			c.JSON(http.StatusServiceUnavailable, gin.H{"status": "degraded"})
			return
		}
		c.JSON(http.StatusOK, gin.H{"status": "ok", "agent_core": health.Status, "version": health.Version})
	})
	v1 := r.engine.Group("/api/v1")
	workspaces := v1.Group("/workspaces/:workspaceID")
	workspaces.Use(r.requireWorkspaceAccess())
	folders := &WorkspaceFolderHandler{client: r.client}
	workspaces.GET("/folders", folders.List)
	workspaces.POST("/folders", r.requireWorkspaceOwner(), folders.Create)
	s := &SessionHandler{client: r.client}
	credentialManager := credentialstore.NewManager(credentialstore.NewOSStore())
	m := &MessageHandler{client: r.client, hub: r.hub, mgr: credentialManager}
	workspaces.GET("/conversations", s.List)
	workspaces.POST("/conversations", s.Create)
	workspaces.GET("/conversations/:conversationID", s.Get)
	workspaces.GET("/conversations/:conversationID/snapshot", s.Snapshot)
	workspaces.PATCH("/conversations/:conversationID", s.Update)
	workspaces.DELETE("/conversations/:conversationID", s.Delete)
	workspaces.GET("/conversations/:conversationID/messages", s.Messages)
	tasks := &TaskHandler{client: r.client}
	workspaces.GET("/tasks", tasks.List)
	workspaces.GET("/tasks/:taskID", tasks.Get)
	inspection := &TaskInspectionHandler{client: r.client}
	workspaces.GET("/capabilities", inspection.Capabilities)
	workspaces.GET("/tasks/:taskID/inspection", inspection.Get)
	workspaces.GET("/tasks/:taskID/inputs", inspection.Inputs)
	workspaces.POST("/tasks/:taskID/inputs", inspection.SubmitInput)
	workspaces.GET("/jobs", inspection.Jobs)
	workspaces.POST("/jobs/:jobID/stop", inspection.StopJob)
	workspaces.POST("/jobs/:jobID/input", inspection.WriteJobInput)
	workspaces.POST("/tasks/:taskID/cancel", tasks.Cancel)
	resume := &TaskResumeHandler{client: r.client, hub: r.hub, mgr: credentialManager}
	workspaces.POST("/tasks/:taskID/resume", r.requireWorkspaceOwner(), resume.Resume)
	workspaces.GET("/conversations/:conversationID/events/history", tasks.Events)
	workspaces.POST("/conversations/:conversationID/messages", m.Send)
	workspaces.GET("/events", m.Stream)
	approvals := &ApprovalHandler{client: r.client, hub: r.hub, mgr: credentialManager}
	workspaces.GET("/approvals", approvals.List)
	workspaces.GET("/approvals/:approvalID", approvals.Get)
	workspaces.POST("/approvals/:approvalID/decision", approvals.Decide)
	workspaces.GET("/approval-authorizations", r.requireWorkspaceOwner(), approvals.ListAuthorizations)
	workspaces.DELETE("/approvals/:approvalID/authorization", r.requireWorkspaceOwner(), approvals.RevokeAuthorization)
	questions := &QuestionHandler{client: r.client, hub: r.hub, mgr: credentialManager}
	workspaces.GET("/questions", questions.List)
	workspaces.POST("/questions/:questionID/answer", questions.Answer)
	workspaces.GET("/audit-events", (&AuditHandler{client: r.client}).List)
	credentials := &CredentialHandler{mgr: credentialManager, client: r.client}
	models := &ModelHandler{mgr: credentialManager, client: r.client}
	preferences := &PreferenceHandler{client: r.client}
	workspaces.GET("/settings", r.requireWorkspaceOwner(), models.GetSettings)
	workspaces.PATCH("/settings", r.requireWorkspaceOwner(), models.UpdateSettings)
	workspaces.GET("/models", models.List)
	workspaces.POST("/models", r.requireWorkspaceOwner(), models.Upsert)
	workspaces.PUT("/models/:modelID", r.requireWorkspaceOwner(), models.Upsert)
	workspaces.DELETE("/models/:modelID", r.requireWorkspaceOwner(), models.Delete)
	workspaces.POST("/models/:modelID/default", r.requireWorkspaceOwner(), models.SetDefault)
	workspaces.POST("/models/actions/validate", r.requireWorkspaceOwner(), models.Validate)
	workspaces.POST("/models/actions/discover", r.requireWorkspaceOwner(), models.Discover)
	workspaces.GET("/credential-references", r.requireWorkspaceOwner(), credentials.Status)
	workspaces.POST("/credential-references", r.requireWorkspaceOwner(), credentials.Save)
	workspaces.PUT("/credential-references/:id", r.requireWorkspaceOwner(), credentials.Update)
	workspaces.DELETE("/credential-references/:id", r.requireWorkspaceOwner(), credentials.Delete)
	workspaces.GET("/preferences", preferences.Get)
	workspaces.PATCH("/preferences", preferences.Update)
	permissions := &PermissionHandler{client: r.client}
	workspaces.GET("/permissions", permissions.Get)
	workspaces.PATCH("/permissions", r.requireWorkspaceOwner(), permissions.Update)
	toolSettings := &ToolSettingsHandler{client: r.client}
	workspaces.GET("/tool-settings", r.requireWorkspaceOwner(), toolSettings.Get)
	workspaces.PATCH("/tool-settings", r.requireWorkspaceOwner(), toolSettings.Update)
	memories := &MemoryHandler{client: r.client}
	workspaces.GET("/memories", memories.List)
	workspaces.POST("/memories", memories.Create)
	workspaces.PATCH("/memories/:memoryID", memories.Update)
	workspaces.DELETE("/memories/:memoryID", memories.Delete)
	workspaces.GET("/data-summary", r.requireWorkspaceOwner(), (&DataHandler{client: r.client}).Summary)
	workspaces.GET("/mcp-servers", (&MCPRuntimeHandler{client: r.client}).List)
	workspaces.GET("/skills", (&SkillHandler{client: r.client}).List)
	extensions := &ExtensionHandler{client: r.client, mgr: credentialManager}
	workspaces.GET("/extension-settings", r.requireWorkspaceOwner(), extensions.Get)
	workspaces.PUT("/extension-settings", r.requireWorkspaceOwner(), extensions.Update)
	workspaces.POST("/extension-settings/apply", r.requireWorkspaceOwner(), extensions.Reload)
	workspace := newWorkspaceHandler(r.cfg.Workspace.Root)
	var runtimeHealth agentHealthReader
	if r.client != nil {
		runtimeHealth = r.client
	}
	runtimeStatus := newRuntimeStatusHandler(r.cfg, workspace, runtimeHealth)
	workspaces.GET("/runtime-status", r.requireWorkspaceOwner(), folders.Files(workspace, func(selected *WorkspaceHandler, c *gin.Context) {
		if selected == workspace {
			runtimeStatus.Get(c)
			return
		}
		handler := newRuntimeStatusHandler(r.cfg, selected, runtimeHealth)
		if c.Query("folder_id") != "" {
			handler.rootSource = "selection"
		}
		handler.Get(c)
	}))
	workspaces.GET("/files", folders.Files(workspace, (*WorkspaceHandler).ListFiles))
	workspaces.GET("/files/content", folders.Files(workspace, (*WorkspaceHandler).ReadFile))
	workspaces.GET("/changes", folders.Files(workspace, (*WorkspaceHandler).Changes))
	workspaces.GET("/changes/diff", folders.Files(workspace, (*WorkspaceHandler).ChangeDiff))
}

func (r *Router) requireWorkspaceOwner() gin.HandlerFunc {
	return func(c *gin.Context) {
		if c.GetString("workspace_role") != "owner" {
			c.AbortWithStatusJSON(http.StatusForbidden, gin.H{"error": gin.H{"code": "ACCESS_DENIED", "message": "workspace owner access is required"}})
			return
		}
		c.Next()
	}
}

func (r *Router) requireWorkspaceAccess() gin.HandlerFunc {
	return func(c *gin.Context) {
		decision, err := r.client.CheckWorkspaceAccess(c.Request.Context(), c.Param("workspaceID"), "local-user")
		if err != nil {
			grpcError(c, err)
			c.Abort()
			return
		}
		if !decision.Allowed {
			c.AbortWithStatusJSON(http.StatusNotFound, gin.H{"error": gin.H{"code": "NOT_FOUND", "message": "workspace not found"}})
			return
		}
		c.Set("principal_id", "local-user")
		c.Set("workspace_role", decision.Role)
		c.Next()
	}
}
