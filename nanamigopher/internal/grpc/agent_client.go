// Package grpc provides the gRPC client for communicating with Python Agent Core.
package grpc

import (
	"context"
	"fmt"
)

// AgentClient manages the gRPC connection to the Python Agent Core process.
type AgentClient struct {
	address string
	// TODO: add actual gRPC connection and generated client in Phase 2
}

// NewAgentClient creates a new agent client connecting to the Python process.
func NewAgentClient(address string) *AgentClient {
	return &AgentClient{address: address}
}

// ProcessMessage sends a message to the Python Agent and returns a response stream.
func (c *AgentClient) ProcessMessage(ctx context.Context, sessionID, content string) (<-chan *AgentResponse, error) {
	ch := make(chan *AgentResponse, 10)
	// TODO: implement actual gRPC streaming call
	go func() {
		defer close(ch)
		ch <- &AgentResponse{
			Type: "error",
			Error: &ErrorInfo{
				Code:    "NOT_IMPLEMENTED",
				Message: "gRPC streaming not yet connected to Python Agent",
			},
		}
	}()
	return ch, nil
}

// CreateSession forwards a session creation request to the Python Agent.
func (c *AgentClient) CreateSession(ctx context.Context, title, modelID, permMode string) (*SessionResponse, error) {
	// TODO: implement gRPC call
	return &SessionResponse{
		Id:    "sess_placeholder",
		Title: title,
	}, nil
}

// ListSessions returns all known sessions.
func (c *AgentClient) ListSessions(ctx context.Context) ([]*SessionResponse, error) {
	// TODO: implement gRPC call
	return nil, nil
}

// AgentResponse represents a streamed response from the Python Agent.
type AgentResponse struct {
	Type  string
	Step  *StepData
	Chunk *MessageChunk
	Error *ErrorInfo
}

// StepData holds step execution information.
type StepData struct {
	Step   string
	Status string
}

// MessageChunk holds a fragment of streamed text output.
type MessageChunk struct {
	Content string
}

// ErrorInfo holds error details from the agent.
type ErrorInfo struct {
	Level     string
	Code      string
	Message   string
	Suggestion string
	Retryable bool
}

// SessionResponse represents a session from the Python Agent.
type SessionResponse struct {
	Id             string
	Title          string
	CreatedAt      string
	UpdatedAt      string
	PermissionMode string
	MessageCount   int32
}

// Empty is a marker for empty gRPC requests.
type Empty struct{}

// Validate checks that the client has a valid address.
func (c *AgentClient) Validate() error {
	if c.address == "" {
		return fmt.Errorf("grpc client: no address configured")
	}
	return nil
}
