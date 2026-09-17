package api

import (
	"context"
	"net/http"
	"os"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/nanamigopher/nanamigopher/gateway/internal/credentialstore"
	agentgrpc "github.com/nanamigopher/nanamigopher/gateway/internal/grpc"
	agentv1 "github.com/nanamigopher/nanamigopher/gateway/pkg/proto/agent/v1"
)

type ModelHandler struct {
	client *agentgrpc.AgentClient
	mgr    *credentialstore.Manager
}

type ChatModelInput struct {
	ID             string  `json:"id" binding:"omitempty,max=86"`
	Name           string  `json:"name" binding:"omitempty,max=80"`
	Provider       string  `json:"provider" binding:"required,oneof=openai anthropic openai_compatible ollama"`
	Model          string  `json:"model" binding:"required,max=200"`
	BaseURL        string  `json:"base_url" binding:"omitempty,max=2048"`
	Temperature    float64 `json:"temperature" binding:"min=0,max=2"`
	MaxTokens      int32   `json:"max_tokens" binding:"required,min=1,max=65536"`
	TimeoutSeconds int32   `json:"timeout_seconds" binding:"required,min=1,max=600"`
	IsDefault      bool    `json:"is_default"`
	APIKey         string  `json:"api_key" binding:"omitempty,max=8192"`
}

type settingsPatchRequest struct {
	Models *struct {
		Chat ChatModelInput `json:"chat" binding:"required"`
	} `json:"models" binding:"required"`
}

type validateModelRequest struct {
	Chat   ChatModelInput `json:"chat" binding:"required"`
	APIKey string         `json:"api_key"`
}

type chatModelResponse struct {
	ID                   string  `json:"id"`
	Name                 string  `json:"name"`
	Provider             string  `json:"provider"`
	Model                string  `json:"model"`
	BaseURL              string  `json:"base_url"`
	Temperature          float64 `json:"temperature"`
	MaxTokens            int32   `json:"max_tokens"`
	TimeoutSeconds       int32   `json:"timeout_seconds"`
	CredentialConfigured bool    `json:"credential_configured"`
	IsDefault            bool    `json:"is_default"`
}

func chatModelProto(input ChatModelInput) *agentv1.ChatModelSettings {
	return &agentv1.ChatModelSettings{
		Id: input.ID, Name: input.Name,
		Provider: input.Provider, Model: input.Model, BaseUrl: input.BaseURL,
		Temperature: input.Temperature, MaxTokens: input.MaxTokens, TimeoutSeconds: input.TimeoutSeconds,
		IsDefault: input.IsDefault,
	}
}

func (h *ModelHandler) responseModel(workspaceID string, settings *agentv1.ChatModelSettings) chatModelResponse {
	key, err := h.mgr.GetModelProfileKeyForWorkspace(workspaceID, settings.Id)
	if settings.Id == "" || (settings.Id == "model_default" && err != nil) {
		key, err = h.mgr.GetModelKeyForWorkspace(workspaceID, settings.Provider)
	}
	configured := err == nil && key != ""
	if !configured && settings.Provider == "openai" {
		configured = os.Getenv("OPENAI_API_KEY") != ""
	} else if !configured && settings.Provider == "anthropic" {
		configured = os.Getenv("ANTHROPIC_API_KEY") != ""
	}
	return chatModelResponse{
		ID: settings.Id, Name: settings.Name,
		Provider: settings.Provider, Model: settings.Model, BaseURL: settings.BaseUrl,
		Temperature: settings.Temperature, MaxTokens: settings.MaxTokens,
		TimeoutSeconds: settings.TimeoutSeconds, CredentialConfigured: configured, IsDefault: settings.IsDefault,
	}
}

func (h *ModelHandler) response(workspaceID string, settings *agentv1.ChatModelSettings) gin.H {
	return gin.H{"models": gin.H{"chat": h.responseModel(workspaceID, settings)}}
}

func sameModelEndpoint(saved *agentv1.ChatModelSettings, provider, baseURL string) bool {
	return saved.Provider == provider &&
		normalizeModelBaseURL(provider, saved.BaseUrl) == normalizeModelBaseURL(provider, baseURL)
}

func (h *ModelHandler) profileAPIKey(
	ctx context.Context, workspaceID, profileID, provider, baseURL string,
) string {
	if profileID == "" {
		return ""
	}
	catalog, err := h.client.ListChatModels(ctx, workspaceID)
	if err != nil {
		return ""
	}
	for _, profile := range catalog.Models {
		if profile.Id != profileID || !sameModelEndpoint(profile, provider, baseURL) {
			continue
		}
		stored, credentialErr := h.mgr.GetModelProfileKeyForWorkspace(workspaceID, profileID)
		if credentialErr == nil && stored != "" {
			return stored
		}
		if profileID == "model_default" {
			stored, credentialErr = h.mgr.GetModelKeyForWorkspace(workspaceID, provider)
			if credentialErr == nil && stored != "" {
				return stored
			}
		}
		if strings.TrimSpace(baseURL) == "" && provider == "openai" {
			return os.Getenv("OPENAI_API_KEY")
		}
		if strings.TrimSpace(baseURL) == "" && provider == "anthropic" {
			return os.Getenv("ANTHROPIC_API_KEY")
		}
		return ""
	}
	return ""
}

func (h *ModelHandler) GetSettings(c *gin.Context) {
	settings, err := h.client.GetChatModelSettings(c.Request.Context(), c.Param("workspaceID"))
	if err != nil {
		grpcError(c, err)
		return
	}
	c.JSON(http.StatusOK, h.response(c.Param("workspaceID"), settings))
}

func (h *ModelHandler) List(c *gin.Context) {
	settings, err := h.client.ListChatModels(c.Request.Context(), c.Param("workspaceID"))
	if err != nil {
		grpcError(c, err)
		return
	}
	models := make([]chatModelResponse, 0, len(settings.Models))
	for _, item := range settings.Models {
		models = append(models, h.responseModel(c.Param("workspaceID"), item))
	}
	c.JSON(http.StatusOK, gin.H{"models": models, "default_model_id": settings.DefaultModelId})
}

func (h *ModelHandler) Upsert(c *gin.Context) {
	var req ChatModelInput
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "VALIDATION", "message": err.Error()}})
		return
	}
	if pathID := c.Param("modelID"); pathID != "" {
		req.ID = pathID
	}
	var previous *agentv1.ChatModelSettings
	if req.ID != "" {
		if catalog, listErr := h.client.ListChatModels(c.Request.Context(), c.Param("workspaceID")); listErr == nil {
			for _, candidate := range catalog.Models {
				if candidate.Id == req.ID {
					previous = candidate
					break
				}
			}
		}
	}
	item, err := h.client.UpsertChatModel(c.Request.Context(), c.Param("workspaceID"), chatModelProto(req))
	if err != nil {
		grpcError(c, err)
		return
	}
	if req.APIKey != "" {
		service := "model-profile." + item.Id
		if err := h.mgr.ValidateAndSaveForWorkspace(c.Param("workspaceID"), service, req.APIKey); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "CREDENTIAL_INVALID", "message": err.Error()}})
			return
		}
		if err := h.client.SetChatModelProfileCredential(c.Request.Context(), c.Param("workspaceID"), item.Id, item.Provider, req.APIKey); err != nil {
			grpcError(c, err)
			return
		}
	} else if previous != nil && (previous.Provider != item.Provider || previous.BaseUrl != item.BaseUrl) {
		_ = h.mgr.DeleteForWorkspace(c.Param("workspaceID"), "model-profile."+item.Id)
		_ = h.client.SetChatModelProfileCredential(c.Request.Context(), c.Param("workspaceID"), item.Id, item.Provider, "")
	}
	_ = h.client.RecordAuditEvent(c.Request.Context(), c.Param("workspaceID"), "local-user", "model.profile.saved", item.Id, "success")
	status := http.StatusOK
	if c.Param("modelID") == "" {
		status = http.StatusCreated
	}
	c.JSON(status, h.responseModel(c.Param("workspaceID"), item))
}

func (h *ModelHandler) Delete(c *gin.Context) {
	modelID := c.Param("modelID")
	if err := h.client.DeleteChatModel(c.Request.Context(), c.Param("workspaceID"), modelID); err != nil {
		grpcError(c, err)
		return
	}
	_ = h.mgr.DeleteForWorkspace(c.Param("workspaceID"), "model-profile."+modelID)
	_ = h.client.SetChatModelProfileCredential(c.Request.Context(), c.Param("workspaceID"), modelID, "", "")
	_ = h.client.RecordAuditEvent(c.Request.Context(), c.Param("workspaceID"), "local-user", "model.profile.deleted", modelID, "success")
	c.Status(http.StatusNoContent)
}

func (h *ModelHandler) SetDefault(c *gin.Context) {
	result, err := h.client.SetDefaultChatModel(c.Request.Context(), c.Param("workspaceID"), c.Param("modelID"))
	if err != nil {
		grpcError(c, err)
		return
	}
	models := make([]chatModelResponse, 0, len(result.Models))
	for _, item := range result.Models {
		models = append(models, h.responseModel(c.Param("workspaceID"), item))
	}
	c.JSON(http.StatusOK, gin.H{"models": models, "default_model_id": result.DefaultModelId})
}

func (h *ModelHandler) UpdateSettings(c *gin.Context) {
	var req settingsPatchRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "VALIDATION", "message": err.Error()}})
		return
	}
	settings, err := h.client.UpdateChatModelSettings(c.Request.Context(), c.Param("workspaceID"), chatModelProto(req.Models.Chat))
	if err != nil {
		grpcError(c, err)
		return
	}
	_ = h.client.RecordAuditEvent(c.Request.Context(), c.Param("workspaceID"), "local-user", "model.settings.updated", settings.Provider+":"+settings.Model, "success")
	c.JSON(http.StatusOK, h.response(c.Param("workspaceID"), settings))
}

func (h *ModelHandler) Validate(c *gin.Context) {
	var req validateModelRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "VALIDATION", "message": err.Error()}})
		return
	}
	apiKey := req.APIKey
	if apiKey == "" {
		apiKey = h.profileAPIKey(
			c.Request.Context(), c.Param("workspaceID"), req.Chat.ID,
			req.Chat.Provider, req.Chat.BaseURL,
		)
	}
	result, err := h.client.ValidateChatModel(c.Request.Context(), chatModelProto(req.Chat), apiKey)
	if err != nil {
		grpcError(c, err)
		return
	}
	status := "failed"
	if result.Ok {
		status = "success"
	}
	_ = h.client.RecordAuditEvent(c.Request.Context(), c.Param("workspaceID"), "local-user", "model.connection.validated", req.Chat.Provider+":"+req.Chat.Model, status)
	c.JSON(http.StatusOK, gin.H{"ok": result.Ok, "message": result.Message, "model": result.Model})
}

func (h *ModelHandler) Discover(c *gin.Context) {
	var req discoverModelRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "VALIDATION", "message": err.Error()}})
		return
	}
	apiKey := req.APIKey
	if apiKey == "" {
		apiKey = h.profileAPIKey(
			c.Request.Context(), c.Param("workspaceID"), req.ID, req.Provider, req.BaseURL,
		)
	}
	models, err := discoverAvailableModels(c.Request.Context(), req.Provider, req.BaseURL, apiKey)
	if err != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": gin.H{"code": "MODEL_DISCOVERY_FAILED", "message": err.Error()}})
		return
	}
	_ = h.client.RecordAuditEvent(c.Request.Context(), c.Param("workspaceID"), "local-user", "model.catalog.discovered", req.Provider, "success")
	c.JSON(http.StatusOK, gin.H{"models": models})
}
