// Package grpc provides the gRPC server stub for Go-to-Python communication.
// In Phase 1, this serves as the interface layer; the actual gRPC server runs in
// the Python Agent Core process, and this package manages the client side.
package grpc

// Server provides the gRPC server infrastructure.
// The Python Agent Core implements the actual gRPC service; this Go side
// acts as a client that connects to the Python process.
type Server struct {
	// In Phase 1, the gRPC server runs inside the Python process.
	// This struct is reserved for future embedded gRPC server usage.
	listenAddr string
}

// NewServer creates a new gRPC server instance.
func NewServer(addr string) *Server {
	return &Server{listenAddr: addr}
}

// Start begins listening on the configured address.
// In Phase 1, this is a no-op since the Python process owns the gRPC server.
func (s *Server) Start() error {
	return nil
}

// Stop gracefully shuts down the gRPC server.
func (s *Server) Stop() {
}
