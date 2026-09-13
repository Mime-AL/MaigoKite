// Package service provides gRPC service implementation stubs.
// The actual gRPC server runs in the Python Agent Core; this package
// is reserved for any Go-side gRPC service implementation.
package service

// AgentService holds the gRPC service implementation.
type AgentService struct {
	// TODO: embed generated grpc service unimplemented server
}

// NewAgentService creates a new AgentService instance.
func NewAgentService() *AgentService {
	return &AgentService{}
}
