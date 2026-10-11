package api

import (
	"context"
	"encoding/json"
	"net/http"

	"github.com/gin-gonic/gin"
	"maigokite/gateway/internal/credentialstore"
	agentgrpc "maigokite/gateway/internal/grpc"
	ws "maigokite/gateway/internal/websocket"
	agentv1 "maigokite/gateway/pkg/proto/agent/v1"
)

type ApprovalHandler struct {
	client *agentgrpc.AgentClient
	hub    *ws.Hub
	mgr    *credentialstore.Manager
}

type approvalResponse struct {
	ID                     string         `json:"id"`
	WorkspaceID            string         `json:"workspace_id"`
	ConversationID         string         `json:"conversation_id"`
	TaskID                 string         `json:"task_id"`
	ToolCallID             string         `json:"tool_call_id"`
	ToolName               string         `json:"tool_name"`
	Arguments              map[string]any `json:"arguments"`
	ResourceScope          string         `json:"resource_scope"`
	RiskLevel              string         `json:"risk_level"`
	Status                 string         `json:"status"`
	Version                int32          `json:"version"`
	ExpiresAt              string         `json:"expires_at"`
	Note                   string         `json:"note"`
	DecidedAt              string         `json:"decided_at"`
	AllowedScopes          []string       `json:"allowed_scopes"`
	ReuseScope             map[string]any `json:"reuse_scope"`
	AuthorizationScope     string         `json:"authorization_scope"`
	AuthorizationExpiresAt string         `json:"authorization_expires_at"`
	AuthorizationRevokedAt string         `json:"authorization_revoked_at"`
}

func approvalValue(item *agentv1.Approval) approvalResponse {
	arguments := map[string]any{}
	_ = json.Unmarshal([]byte(item.ArgumentsJson), &arguments)
	reuse := map[string]any{}
	_ = json.Unmarshal([]byte(item.ReuseScopeJson), &reuse)
	return approvalResponse{
		ID: item.Id, WorkspaceID: item.WorkspaceId, ConversationID: item.ConversationId,
		TaskID: item.TaskId, ToolCallID: item.ToolCallId, ToolName: item.ToolName,
		Arguments: arguments, ResourceScope: item.ResourceScope, RiskLevel: item.RiskLevel,
		Status: item.Status, Version: item.Version, ExpiresAt: item.ExpiresAt,
		Note: item.Note, DecidedAt: item.DecidedAt,
		AllowedScopes: item.AllowedScopes, ReuseScope: reuse, AuthorizationScope: item.AuthorizationScope,
		AuthorizationExpiresAt: item.AuthorizationExpiresAt, AuthorizationRevokedAt: item.AuthorizationRevokedAt,
	}
}

func (h *ApprovalHandler) Get(c *gin.Context) {
	item, err := h.client.GetApproval(c.Request.Context(), c.Param("workspaceID"), c.Param("approvalID"))
	if err != nil {
		grpcError(c, err)
		return
	}
	c.JSON(http.StatusOK, approvalValue(item))
}

func (h *ApprovalHandler) List(c *gin.Context) {
	items, err := h.client.ListApprovals(c.Request.Context(), c.Param("workspaceID"), c.Query("conversation_id"))
	if err != nil {
		grpcError(c, err)
		return
	}
	result := make([]approvalResponse, 0, len(items.Approvals))
	for _, item := range items.Approvals {
		result = append(result, approvalValue(item))
	}
	c.JSON(http.StatusOK, gin.H{"approvals": result})
}

type approvalDecisionRequest struct {
	Decision string `json:"decision" binding:"required,oneof=allow deny"`
	Version  int32  `json:"version" binding:"required,min=1"`
	Note     string `json:"note" binding:"max=2000"`
	Scope    string `json:"scope" binding:"omitempty,oneof=once task session"`
}

func (h *ApprovalHandler) Decide(c *gin.Context) {
	var req approvalDecisionRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "VALIDATION", "message": err.Error()}})
		return
	}
	if req.Scope == "" {
		req.Scope = "once"
	}
	if req.Decision == "deny" && req.Scope != "once" {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "VALIDATION", "message": "denial cannot create an authorization"}})
		return
	}
	// Resolve the pending approval before accepting a decision. The Core remains
	// authoritative for ownership, version and argument-hash validation.
	pending, err := h.client.GetApproval(c.Request.Context(), c.Param("workspaceID"), c.Param("approvalID"))
	if err != nil {
		grpcError(c, err)
		return
	}
	conversationID := pending.ConversationId
	if pending.Status != "pending" || pending.Version != req.Version {
		c.JSON(http.StatusConflict, gin.H{"error": gin.H{"code": "APPROVAL_NOT_PENDING", "message": "approval is no longer pending; refresh its status"}})
		return
	}
	if req.Scope != "once" {
		allowed := false
		for _, scope := range pending.AllowedScopes {
			if scope == req.Scope {
				allowed = true
			}
		}
		if !allowed {
			c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "APPROVAL_SCOPE_UNAVAILABLE", "message": "this operation only supports one-time approval"}})
			return
		}
	}
	// A refusal must work even if the model was removed or the keychain is locked.
	if req.Decision == "allow" {
		if err := prepareExecutionCredentials(c.Request.Context(), h.client, h.mgr, c.Param("workspaceID"), conversationID, pending.TaskId); err != nil {
			grpcError(c, err)
			return
		}
		if err := prepareMCPApproval(c.Request.Context(), h.client, h.mgr, c.Param("workspaceID"), pending.ToolName); err != nil {
			grpcError(c, err)
			return
		}
	} else {
		// Best effort after a Core restart. Refusal must still be saved if the
		// keychain/model is unavailable; Core reports any continuation failure
		// through task.failed after approval.decided, never by granting the tool.
		_ = prepareExecutionModelCredentials(c.Request.Context(), h.client, h.mgr, c.Param("workspaceID"), conversationID, pending.TaskId)
	}
	streamContext, cancel := context.WithCancel(context.Background())
	events, errs := h.client.DecideApproval(streamContext, &agentv1.ApprovalDecisionRequest{
		WorkspaceId: c.Param("workspaceID"), ApprovalId: c.Param("approvalID"),
		PrincipalId: c.GetString("principal_id"), Decision: req.Decision, Version: req.Version,
		Note: req.Note, Scope: req.Scope,
	})
	first, ok := <-events
	if !ok {
		cancel()
		if err := <-errs; err != nil {
			grpcError(c, err)
			return
		}
		c.JSON(http.StatusBadGateway, gin.H{"error": gin.H{"code": "EMPTY_STREAM", "message": "agent returned no event"}})
		return
	}
	if first.Type == "error" {
		cancel()
		c.JSON(http.StatusBadGateway, gin.H{"error": gin.H{"code": first.Code, "message": first.Message}})
		return
	}
	forwardExecutionEvents(h.hub, first, events, errs, cancel)
	c.JSON(http.StatusAccepted, gin.H{"approval_id": c.Param("approvalID"), "task_id": first.TaskId, "status": "processing"})
}

func (h *ApprovalHandler) ListAuthorizations(c *gin.Context) {
	conversationID := c.Query("conversation_id")
	if conversationID == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "VALIDATION", "message": "conversation_id is required"}})
		return
	}
	items, err := h.client.ListApprovalAuthorizations(c.Request.Context(), &agentv1.ApprovalAuthorizationRequest{
		WorkspaceId: c.Param("workspaceID"), ConversationId: conversationID, PrincipalId: c.GetString("principal_id"),
	})
	if err != nil {
		grpcError(c, err)
		return
	}
	var values []map[string]any
	if err := json.Unmarshal([]byte(items.Json), &values); err != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": gin.H{"code": "INVALID_RESPONSE", "message": "invalid authorization response"}})
		return
	}
	c.JSON(http.StatusOK, gin.H{"authorizations": values})
}

func (h *ApprovalHandler) RevokeAuthorization(c *gin.Context) {
	if err := h.client.RevokeApprovalAuthorization(c.Request.Context(), &agentv1.ApprovalAuthorizationRequest{
		WorkspaceId: c.Param("workspaceID"), ApprovalId: c.Param("approvalID"), PrincipalId: c.GetString("principal_id"),
	}); err != nil {
		grpcError(c, err)
		return
	}
	c.Status(http.StatusNoContent)
}
