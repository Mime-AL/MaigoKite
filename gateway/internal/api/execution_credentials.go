package api

import (
	"context"
	"fmt"

	"maigokite/gateway/internal/credentialstore"
	agentgrpc "maigokite/gateway/internal/grpc"
	agentv1 "maigokite/gateway/pkg/proto/agent/v1"
)

// prepareExecutionCredentials is shared by new messages and approval resumes.
// Core credentials are process-local; neither path may assume a previous run
// populated them. Secrets stay out of task state and approval/checkpoint data.
func prepareExecutionCredentials(ctx context.Context, client *agentgrpc.AgentClient, mgr *credentialstore.Manager, workspaceID, conversationID string) error {
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
	if mgr == nil {
		return fmt.Errorf("credential store is unavailable")
	}
	for _, settings := range catalog.Models {
		if settings.Id != selectedID {
			continue
		}
		apiKey, keyErr := mgr.GetModelProfileKeyForWorkspace(workspaceID, settings.Id)
		if keyErr != nil && settings.Id == "model_default" {
			apiKey, _ = mgr.GetModelKeyForWorkspace(workspaceID, settings.Provider)
		}
		if err := client.SetChatModelProfileCredential(ctx, workspaceID, settings.Id, settings.Provider, apiKey); err != nil {
			return err
		}
		break
	}
	for _, service := range []string{"tavily", "google"} {
		apiKey, _ := mgr.GetSearchKeyForWorkspace(workspaceID, service)
		if err := client.SetToolCredential(ctx, workspaceID, service, apiKey); err != nil {
			return err
		}
	}
	return nil
}
