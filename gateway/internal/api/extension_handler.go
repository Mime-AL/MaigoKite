package api

import (
	"encoding/json"
	"net/http"

	"github.com/gin-gonic/gin"
	"maigokite/gateway/internal/credentialstore"
	agentgrpc "maigokite/gateway/internal/grpc"
)

// Core owns desired/applied configuration. Gateway resolves keychain references
// for an explicit apply/restore or before continuing a pending MCP approval.
type ExtensionHandler struct {
	client *agentgrpc.AgentClient
	mgr    *credentialstore.Manager
}

type extensionConfigView struct {
	Revision int64 `json:"revision"`
	Servers  []struct {
		Namespace string   `json:"namespace"`
		Enabled   bool     `json:"enabled"`
		SecretEnv []string `json:"secret_env"`
	} `json:"mcp_servers"`
}

type extensionSnapshot struct {
	Config       extensionConfigView  `json:"config"`
	ActiveConfig *extensionConfigView `json:"active_config"`
	Servers      []struct {
		Namespace string `json:"namespace"`
		Status    string `json:"status"`
	} `json:"servers"`
}

func extensionCredentials(mgr *credentialstore.Manager, workspace string, config extensionConfigView) map[string]map[string]string {
	credentials := map[string]map[string]string{}
	if mgr == nil {
		return credentials
	}
	for _, server := range config.Servers {
		if !server.Enabled {
			continue
		}
		credentials[server.Namespace] = map[string]string{}
		for _, name := range server.SecretEnv {
			secret, err := mgr.GetForWorkspace(workspace, "mcp."+server.Namespace+"."+name)
			if err == nil && secret != "" {
				credentials[server.Namespace][name] = secret
			}
		}
	}
	return credentials
}

func (h *ExtensionHandler) Get(c *gin.Context) {
	value, err := h.client.GetExtensions(c.Request.Context(), c.Param("workspaceID"))
	if err != nil {
		grpcError(c, err)
		return
	}
	c.Data(http.StatusOK, "application/json", []byte(value.Json))
}

func (h *ExtensionHandler) Update(c *gin.Context) {
	c.Request.Body = http.MaxBytesReader(c.Writer, c.Request.Body, 2<<20)
	var config json.RawMessage
	if err := c.ShouldBindJSON(&config); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "VALIDATION", "message": "Invalid extension configuration"}})
		return
	}
	value, err := h.client.UpdateExtensions(c.Request.Context(), c.Param("workspaceID"), string(config))
	if err != nil {
		grpcError(c, err)
		return
	}
	c.Data(http.StatusOK, "application/json", []byte(value.Json))
}

func (h *ExtensionHandler) Reload(c *gin.Context) {
	c.Request.Body = http.MaxBytesReader(c.Writer, c.Request.Body, 4096)
	var request struct {
		Revision    *int64 `json:"revision"`
		RestoreOnly bool   `json:"restore_only"`
	}
	if c.ShouldBindJSON(&request) != nil || request.Revision == nil || *request.Revision < 0 {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "VALIDATION", "message": "A saved revision is required"}})
		return
	}
	workspace := c.Param("workspaceID")
	settings, err := h.client.GetExtensions(c.Request.Context(), workspace)
	if err != nil {
		grpcError(c, err)
		return
	}
	var snapshot extensionSnapshot
	if json.Unmarshal([]byte(settings.Json), &snapshot) != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": "Invalid Core extension response"})
		return
	}
	config := snapshot.Config
	if request.RestoreOnly {
		if snapshot.ActiveConfig == nil {
			c.JSON(http.StatusConflict, gin.H{"error": "No applied extension configuration is available"})
			return
		}
		config = *snapshot.ActiveConfig
	}
	if config.Revision != *request.Revision {
		c.JSON(http.StatusConflict, gin.H{"error": "Extension settings changed; refresh before applying"})
		return
	}
	credentials := extensionCredentials(h.mgr, workspace, config)
	encoded, _ := json.Marshal(credentials)
	value, err := h.client.ReloadExtensions(c.Request.Context(), workspace, *request.Revision, string(encoded), request.RestoreOnly)
	if err != nil {
		grpcError(c, err)
		return
	}
	c.Data(http.StatusOK, "application/json", []byte(value.Json))
}
