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

// prepareExecutionCredentials is shared by new messages, approvals and task recovery.
// Core credentials are process-local; no entry may assume a previous run
// populated them. Secrets stay out of task state and approval/checkpoint data.
func prepareExecutionCredentials(ctx context.Context, client *agentgrpc.AgentClient, mgr *credentialstore.Manager, workspaceID, conversationID string, taskIDs ...string) error {
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
	for _, service := range []string{"tavily", "google"} {
		apiKey, _ := mgr.GetSearchKeyForWorkspace(workspaceID, service)
		if err := client.SetToolCredential(ctx, workspaceID, service, apiKey); err != nil {
			return err
		}
	}
	return nil
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
