package api

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"

	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"

	"maigokite/gateway/internal/credentialstore"
	agentgrpc "maigokite/gateway/internal/grpc"
	agentv1 "maigokite/gateway/pkg/proto/agent/v1"
)

// Thinking discovery and settings validation also work immediately after Core
// restart. Restore only this model, without starting extensions or generation.
func prepareChatModelCredential(ctx context.Context, client *agentgrpc.AgentClient, mgr *credentialstore.Manager, workspaceID, modelID string) error {
	catalog, err := client.ListChatModels(ctx, workspaceID)
	if err != nil {
		return err
	}
	if modelID == "" {
		modelID = catalog.DefaultModelId
	}
	for _, settings := range catalog.Models {
		if settings.Id != modelID {
			continue
		}
		if mgr == nil {
			return fmt.Errorf("credential store is unavailable")
		}
		key, keyErr := mgr.GetModelProfileKeyForWorkspace(workspaceID, settings.Id)
		if keyErr != nil && settings.Id == "model_default" {
			key, _ = mgr.GetModelKeyForWorkspace(workspaceID, settings.Provider)
		}
		return client.SetChatModelProfileCredential(ctx, workspaceID, settings.Id, settings.Provider, key)
	}
	return status.Error(codes.NotFound, "model profile not found")
}

// prepareExecutionCredentials is shared by new messages, approvals and task recovery.
// Core credentials are process-local; no entry may assume a previous run
// populated them. Secrets stay out of task state and approval/checkpoint data.
func prepareExecutionCredentials(ctx context.Context, client *agentgrpc.AgentClient, mgr *credentialstore.Manager, workspaceID, conversationID string, taskIDs ...string) error {
	if err := prepareExecutionModelCredentials(ctx, client, mgr, workspaceID, conversationID, taskIDs...); err != nil {
		return err
	}
	for _, service := range []string{"tavily", "google"} {
		apiKey, _ := mgr.GetSearchKeyForWorkspace(workspaceID, service)
		if err := client.SetToolCredential(ctx, workspaceID, service, apiKey); err != nil {
			return err
		}
	}
	return prepareActiveExtensions(ctx, client, mgr, workspaceID)
}

// Denial resumes the model too, but must not start the declined MCP service or
// depend on that service's credentials. Reuse just the model credential step.
func prepareExecutionModelCredentials(ctx context.Context, client *agentgrpc.AgentClient, mgr *credentialstore.Manager, workspaceID, conversationID string, taskIDs ...string) error {
	conversation, err := client.GetConversation(ctx, &agentv1.ConversationRequest{WorkspaceId: workspaceID, ConversationId: conversationID})
	if err != nil {
		return err
	}
	catalog, err := client.ListChatModels(ctx, workspaceID)
	if err != nil {
		return err
	}
	selectedID := conversation.ModelId
	if selectedID == "" {
		selectedID = catalog.DefaultModelId
	}
	childModels := conversation.SubagentModelIds
	if len(taskIDs) > 0 {
		task, err := client.GetTask(ctx, workspaceID, taskIDs[0])
		if err != nil {
			return err
		}
		if task.ConversationId != conversationID {
			return fmt.Errorf("task does not belong to the conversation")
		}
		// Settings changed while an approval was pending must not replace the
		// admitted turn's model policy after a Core restart.
		childModels = task.SubagentModelIds
	}
	selected := map[string]bool{selectedID: true}
	for _, id := range childModels {
		selected[id] = true
	}
	if mgr == nil {
		return fmt.Errorf("credential store is unavailable")
	}
	for _, settings := range catalog.Models {
		if !selected[settings.Id] {
			continue
		}
		apiKey, keyErr := mgr.GetModelProfileKeyForWorkspace(workspaceID, settings.Id)
		if keyErr != nil && settings.Id == "model_default" {
			apiKey, _ = mgr.GetModelKeyForWorkspace(workspaceID, settings.Provider)
		}
		if err := client.SetChatModelProfileCredential(ctx, workspaceID, settings.Id, settings.Provider, apiKey); err != nil {
			return err
		}
	}
	return nil
}

// Restore only the last-applied catalog, never saved-but-unapplied edits. This
// runs before admission (including recovery), while Core can safely reconnect.
func prepareActiveExtensions(ctx context.Context, client *agentgrpc.AgentClient, mgr *credentialstore.Manager, workspaceID string) error {
	settings, err := client.GetExtensions(ctx, workspaceID)
	if err != nil {
		return err
	}
	var snapshot extensionSnapshot
	if err := json.Unmarshal([]byte(settings.Json), &snapshot); err != nil || snapshot.ActiveConfig == nil {
		return status.Error(codes.FailedPrecondition, "无法读取已生效的扩展配置。")
	}
	ready := map[string]bool{}
	for _, server := range snapshot.Servers {
		ready[server.Namespace] = server.Status == "running"
	}
	restore := false
	for _, server := range snapshot.ActiveConfig.Servers {
		if server.Enabled && !ready[server.Namespace] {
			restore = true
		}
	}
	if !restore {
		return nil
	}
	credentials := extensionCredentials(mgr, workspaceID, *snapshot.ActiveConfig)
	for _, server := range snapshot.ActiveConfig.Servers {
		if !server.Enabled {
			continue
		}
		for _, name := range server.SecretEnv {
			if credentials[server.Namespace][name] == "" {
				return status.Error(codes.FailedPrecondition, "MCP 凭证尚未恢复，请解锁密钥链或在扩展设置中补齐凭证；任务尚未提交。")
			}
		}
	}
	encoded, err := json.Marshal(credentials)
	if err != nil {
		return err
	}
	_, err = client.ReloadExtensions(ctx, workspaceID, snapshot.ActiveConfig.Revision, string(encoded), true)
	return err
}

// Rehydrate a pending MCP approval against the last-applied configuration only.
// Do not reapply saved edits or consume the decision on connection failure.
func prepareMCPApproval(ctx context.Context, client *agentgrpc.AgentClient, mgr *credentialstore.Manager, workspaceID, toolName string) error {
	namespace, _, isMCP := strings.Cut(toolName, "__")
	if !isMCP {
		return nil
	}
	settings, err := client.GetExtensions(ctx, workspaceID)
	if err != nil {
		return err
	}
	var snapshot extensionSnapshot
	if json.Unmarshal([]byte(settings.Json), &snapshot) != nil || snapshot.ActiveConfig == nil {
		return status.Error(codes.FailedPrecondition, "无法读取已生效的扩展配置，请刷新或重启服务。")
	}
	for _, server := range snapshot.Servers {
		if server.Namespace == namespace && server.Status == "running" {
			return nil
		}
	}
	if mgr == nil {
		return status.Error(codes.FailedPrecondition, "系统密钥链不可用。")
	}
	credentials := extensionCredentials(mgr, workspaceID, *snapshot.ActiveConfig)
	found := false
	for _, server := range snapshot.ActiveConfig.Servers {
		if server.Namespace != namespace || !server.Enabled {
			continue
		}
		found = true
		for _, name := range server.SecretEnv {
			if credentials[namespace][name] == "" {
				return status.Error(codes.FailedPrecondition, "请先解锁密钥链或补齐此 MCP 的凭证；审批尚未提交。")
			}
		}
	}
	if !found {
		return status.Error(codes.FailedPrecondition, "审批对应的 MCP 已停用或移除，请取消此任务。")
	}
	encoded, _ := json.Marshal(credentials)
	result, err := client.ReloadExtensions(ctx, workspaceID, snapshot.ActiveConfig.Revision, string(encoded), true)
	if err != nil {
		return err
	}
	if json.Unmarshal([]byte(result.Json), &snapshot) == nil {
		for _, server := range snapshot.Servers {
			if server.Namespace == namespace && server.Status == "running" {
				return nil
			}
		}
	}
	return status.Error(codes.FailedPrecondition, "MCP 连接尚未恢复，请检查扩展状态；审批尚未提交。")
}
