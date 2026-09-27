// Package grpc owns the Gateway client connection to Python Agent Core.
package grpc

import (
	"context"
	"fmt"
	"io"

	agentv1 "github.com/nanamigopher/nanamigopher/gateway/pkg/proto/agent/v1"

	grpcgo "google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

type AgentClient struct {
	address string
	conn    *grpcgo.ClientConn
	client  agentv1.AgentServiceClient
}

func DialAgentClient(ctx context.Context, address string) (*AgentClient, error) {
	if address == "" {
		return nil, fmt.Errorf("grpc client: no address configured")
	}
	conn, err := grpcgo.DialContext(ctx, address, grpcgo.WithTransportCredentials(insecure.NewCredentials()), grpcgo.WithBlock())
	if err != nil {
		return nil, fmt.Errorf("connect agent core: %w", err)
	}
	return &AgentClient{address: address, conn: conn, client: agentv1.NewAgentServiceClient(conn)}, nil
}

func (c *AgentClient) Close() error {
	if c.conn == nil {
		return nil
	}
	return c.conn.Close()
}
func (c *AgentClient) Validate() error {
	if c == nil || c.client == nil {
		return fmt.Errorf("grpc client is not connected")
	}
	return nil
}

func (c *AgentClient) ProcessMessage(ctx context.Context, request *agentv1.ProcessMessageRequest) (<-chan *agentv1.AgentEvent, <-chan error) {
	events := make(chan *agentv1.AgentEvent, 16)
	errors := make(chan error, 1)
	go func() {
		defer close(events)
		defer close(errors)
		stream, err := c.client.ProcessMessage(ctx, request)
		if err != nil {
			errors <- err
			return
		}
		for {
			event, err := stream.Recv()
			if err == io.EOF {
				return
			}
			if err != nil {
				errors <- err
				return
			}
			select {
			case events <- event:
			case <-ctx.Done():
				errors <- ctx.Err()
				return
			}
		}
	}()
	return events, errors
}

func (c *AgentClient) CreateConversation(ctx context.Context, req *agentv1.ConversationRequest) (*agentv1.Conversation, error) {
	return c.client.CreateConversation(ctx, req)
}
func (c *AgentClient) GetConversation(ctx context.Context, req *agentv1.ConversationRequest) (*agentv1.Conversation, error) {
	return c.client.GetConversation(ctx, req)
}
func (c *AgentClient) ListConversations(ctx context.Context, workspaceID string) (*agentv1.ConversationList, error) {
	return c.client.ListConversations(ctx, &agentv1.ListConversationsRequest{WorkspaceId: workspaceID})
}
func (c *AgentClient) DeleteConversation(ctx context.Context, req *agentv1.ConversationRequest) error {
	_, err := c.client.DeleteConversation(ctx, req)
	return err
}
func (c *AgentClient) UpdateConversationPermission(ctx context.Context, req *agentv1.ConversationPermissionRequest) (*agentv1.Conversation, error) {
	return c.client.UpdateConversationPermission(ctx, req)
}
func (c *AgentClient) UpdateConversationSettings(ctx context.Context, req *agentv1.ConversationSettingsRequest) (*agentv1.Conversation, error) {
	return c.client.UpdateConversationSettings(ctx, req)
}
func (c *AgentClient) ListMessages(ctx context.Context, req *agentv1.ConversationRequest) (*agentv1.MessageList, error) {
	return c.client.ListMessages(ctx, req)
}
func (c *AgentClient) GetTask(ctx context.Context, workspaceID, taskID string) (*agentv1.Task, error) {
	return c.client.GetTask(ctx, &agentv1.TaskRequest{WorkspaceId: workspaceID, TaskId: taskID})
}
func (c *AgentClient) ListTasks(ctx context.Context, workspaceID, conversationID string, limit int32) (*agentv1.TaskList, error) {
	return c.client.ListTasks(ctx, &agentv1.TaskListRequest{WorkspaceId: workspaceID, ConversationId: conversationID, Limit: limit})
}
func (c *AgentClient) CancelTask(ctx context.Context, workspaceID, taskID string) (*agentv1.Task, error) {
	return c.client.CancelTask(ctx, &agentv1.TaskRequest{WorkspaceId: workspaceID, TaskId: taskID})
}
func (c *AgentClient) ListTaskEvents(ctx context.Context, workspaceID, conversationID string, afterSequence int64, limit int32) (*agentv1.TaskEventList, error) {
	return c.client.ListTaskEvents(ctx, &agentv1.TaskEventListRequest{WorkspaceId: workspaceID, ConversationId: conversationID, AfterSequence: afterSequence, Limit: limit})
}
func (c *AgentClient) Health(ctx context.Context) (*agentv1.HealthResponse, error) {
	return c.client.Health(ctx, &agentv1.Empty{})
}
func (c *AgentClient) CheckWorkspaceAccess(ctx context.Context, workspaceID, principalID string) (*agentv1.WorkspaceAccessResponse, error) {
	return c.client.CheckWorkspaceAccess(ctx, &agentv1.WorkspaceAccessRequest{WorkspaceId: workspaceID, PrincipalId: principalID})
}
func (c *AgentClient) ListAuditEvents(ctx context.Context, workspaceID string) (*agentv1.AuditEventList, error) {
	return c.client.ListAuditEvents(ctx, &agentv1.ListConversationsRequest{WorkspaceId: workspaceID})
}
func (c *AgentClient) RecordAuditEvent(ctx context.Context, workspaceID, actor, action, resource, result string) error {
	_, err := c.client.RecordAuditEvent(ctx, &agentv1.AuditWriteRequest{WorkspaceId: workspaceID, Actor: actor, Action: action, Resource: resource, Result: result})
	return err
}
func (c *AgentClient) GetChatModelSettings(ctx context.Context, workspaceID string) (*agentv1.ChatModelSettings, error) {
	return c.client.GetChatModelSettings(ctx, &agentv1.WorkspaceRequest{WorkspaceId: workspaceID})
}
func (c *AgentClient) UpdateChatModelSettings(ctx context.Context, workspaceID string, settings *agentv1.ChatModelSettings) (*agentv1.ChatModelSettings, error) {
	return c.client.UpdateChatModelSettings(ctx, &agentv1.UpdateChatModelSettingsRequest{WorkspaceId: workspaceID, Settings: settings})
}
func (c *AgentClient) ListChatModels(ctx context.Context, workspaceID string) (*agentv1.ChatModelList, error) {
	return c.client.ListChatModels(ctx, &agentv1.WorkspaceRequest{WorkspaceId: workspaceID})
}
func (c *AgentClient) UpsertChatModel(ctx context.Context, workspaceID string, settings *agentv1.ChatModelSettings) (*agentv1.ChatModelSettings, error) {
	return c.client.UpsertChatModel(ctx, &agentv1.UpsertChatModelRequest{WorkspaceId: workspaceID, Settings: settings})
}
func (c *AgentClient) DeleteChatModel(ctx context.Context, workspaceID, modelID string) error {
	_, err := c.client.DeleteChatModel(ctx, &agentv1.ChatModelRequest{WorkspaceId: workspaceID, ModelId: modelID})
	return err
}
func (c *AgentClient) SetDefaultChatModel(ctx context.Context, workspaceID, modelID string) (*agentv1.ChatModelList, error) {
	return c.client.SetDefaultChatModel(ctx, &agentv1.ChatModelRequest{WorkspaceId: workspaceID, ModelId: modelID})
}
func (c *AgentClient) ValidateChatModel(ctx context.Context, settings *agentv1.ChatModelSettings, apiKey string) (*agentv1.ModelValidationResponse, error) {
	return c.client.ValidateChatModel(ctx, &agentv1.ValidateChatModelRequest{Settings: settings, ApiKey: apiKey})
}
func (c *AgentClient) SetChatModelCredential(ctx context.Context, workspaceID, provider, apiKey string) error {
	_, err := c.client.SetChatModelCredential(ctx, &agentv1.SetChatModelCredentialRequest{WorkspaceId: workspaceID, ApiKey: apiKey, Provider: provider})
	return err
}
func (c *AgentClient) SetChatModelProfileCredential(ctx context.Context, workspaceID, modelID, provider, apiKey string) error {
	_, err := c.client.SetChatModelCredential(ctx, &agentv1.SetChatModelCredentialRequest{
		WorkspaceId: workspaceID, ApiKey: apiKey, Provider: provider, ModelId: modelID,
	})
	return err
}
func (c *AgentClient) SetToolCredential(ctx context.Context, workspaceID, service, apiKey string) error {
	_, err := c.client.SetToolCredential(ctx, &agentv1.SetToolCredentialRequest{
		WorkspaceId: workspaceID, Service: service, ApiKey: apiKey,
	})
	return err
}
func (c *AgentClient) GetUserPreferences(ctx context.Context, workspaceID, subjectUserID string) (*agentv1.UserPreferences, error) {
	return c.client.GetUserPreferences(ctx, &agentv1.UserPreferencesRequest{WorkspaceId: workspaceID, SubjectUserId: subjectUserID})
}
func (c *AgentClient) UpdateUserPreferences(ctx context.Context, workspaceID, subjectUserID, assistantName string) (*agentv1.UserPreferences, error) {
	return c.client.UpdateUserPreferences(ctx, &agentv1.UpdateUserPreferencesRequest{
		WorkspaceId: workspaceID, SubjectUserId: subjectUserID,
		Preferences: &agentv1.UserPreferences{AssistantName: assistantName},
	})
}

func (c *AgentClient) ListApprovals(ctx context.Context, workspaceID, conversationID string) (*agentv1.ApprovalList, error) {
	return c.client.ListApprovals(ctx, &agentv1.ApprovalListRequest{WorkspaceId: workspaceID, ConversationId: conversationID})
}

func (c *AgentClient) DecideApproval(ctx context.Context, request *agentv1.ApprovalDecisionRequest) (<-chan *agentv1.AgentEvent, <-chan error) {
	events := make(chan *agentv1.AgentEvent, 16)
	errors := make(chan error, 1)
	go func() {
		defer close(events)
		defer close(errors)
		stream, err := c.client.DecideApproval(ctx, request)
		if err != nil {
			errors <- err
			return
		}
		for {
			event, err := stream.Recv()
			if err == io.EOF {
				return
			}
			if err != nil {
				errors <- err
				return
			}
			select {
			case events <- event:
			case <-ctx.Done():
				errors <- ctx.Err()
				return
			}
		}
	}()
	return events, errors
}

func (c *AgentClient) GetPermissionSettings(ctx context.Context, workspaceID string) (*agentv1.PermissionSettings, error) {
	return c.client.GetPermissionSettings(ctx, &agentv1.WorkspaceRequest{WorkspaceId: workspaceID})
}

func (c *AgentClient) UpdatePermissionSettings(ctx context.Context, workspaceID string, settings *agentv1.PermissionSettings) (*agentv1.PermissionSettings, error) {
	return c.client.UpdatePermissionSettings(ctx, &agentv1.UpdatePermissionSettingsRequest{WorkspaceId: workspaceID, Settings: settings})
}

func (c *AgentClient) ListMemories(ctx context.Context, workspaceID, subjectUserID, query string, limit int32) (*agentv1.MemoryList, error) {
	return c.client.ListMemories(ctx, &agentv1.MemoryListRequest{
		WorkspaceId: workspaceID, SubjectUserId: subjectUserID, Query: query, Limit: limit,
	})
}

func (c *AgentClient) UpsertMemory(ctx context.Context, workspaceID, subjectUserID string, memory *agentv1.Memory) (*agentv1.Memory, error) {
	return c.client.UpsertMemory(ctx, &agentv1.UpsertMemoryRequest{
		WorkspaceId: workspaceID, SubjectUserId: subjectUserID, Memory: memory,
	})
}

func (c *AgentClient) DeleteMemory(ctx context.Context, workspaceID, subjectUserID, memoryID string) error {
	_, err := c.client.DeleteMemory(ctx, &agentv1.MemoryRequest{
		WorkspaceId: workspaceID, SubjectUserId: subjectUserID, MemoryId: memoryID,
	})
	return err
}

func (c *AgentClient) GetWorkspaceDataSummary(ctx context.Context, workspaceID string) (*agentv1.WorkspaceDataSummary, error) {
	return c.client.GetWorkspaceDataSummary(ctx, &agentv1.WorkspaceRequest{WorkspaceId: workspaceID})
}

func (c *AgentClient) ListMCPServers(ctx context.Context, workspaceID string) (*agentv1.MCPServerList, error) {
	return c.client.ListMCPServers(ctx, &agentv1.WorkspaceRequest{WorkspaceId: workspaceID})
}

func (c *AgentClient) ListSkills(ctx context.Context, workspaceID string) (*agentv1.SkillList, error) {
	return c.client.ListSkills(ctx, &agentv1.WorkspaceRequest{WorkspaceId: workspaceID})
}
