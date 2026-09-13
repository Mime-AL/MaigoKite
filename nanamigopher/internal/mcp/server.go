// Package mcp provides MCP Server protocol abstraction.
package mcp

import (
	"context"
	"encoding/json"
)

// Server wraps an MCP Server process with JSON-RPC communication methods.
type Server struct {
	name    string
	stdin   *jsonWriter
	stdout  *jsonReader
	stderr  *jsonReader
}

// jsonWriter wraps a process stdin for writing JSON-RPC messages.
type jsonWriter struct{}

func (w *jsonWriter) Write(ctx context.Context, msg json.RawMessage) error {
	_ = ctx
	_ = msg
	// TODO: write to process stdin
	return nil
}

// jsonReader wraps a process stdout for reading JSON-RPC responses.
type jsonReader struct{}

func (r *jsonReader) Read(ctx context.Context) (json.RawMessage, error) {
	_ = ctx
	// TODO: read from process stdout
	return nil, nil
}

// Tool represents an MCP-discovered tool.
type Tool struct {
	Name        string          `json:"name"`
	Description string          `json:"description"`
	InputSchema json.RawMessage `json:"inputSchema"`
}

// CallRequest is a JSON-RPC request to call an MCP tool.
type CallRequest struct {
	JSONRPC string                 `json:"jsonrpc"`
	ID      int                    `json:"id"`
	Method  string                 `json:"method"`
	Params  map[string]interface{} `json:"params"`
}

// CallResponse is a JSON-RPC response from an MCP tool call.
type CallResponse struct {
	JSONRPC string      `json:"jsonrpc"`
	ID      int         `json:"id"`
	Result  ToolResult  `json:"result"`
	Error   *CallError  `json:"error,omitempty"`
}

// ToolResult holds the result of a tool invocation.
type ToolResult struct {
	Content []ContentItem `json:"content"`
}

// ContentItem is a piece of content returned by a tool.
type ContentItem struct {
	Type string `json:"type"` // text, image, etc.
	Text string `json:"text,omitempty"`
}

// CallError is an error returned by an MCP tool.
type CallError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

// DiscoverTools sends a tools/list request and returns available tools.
func (s *Server) DiscoverTools(ctx context.Context) ([]Tool, error) {
	// TODO: send JSON-RPC tools/list, parse response
	_ = ctx
	return nil, nil
}

// CallTool sends a tools/call request with the given tool name and arguments.
func (s *Server) CallTool(ctx context.Context, name string, args map[string]interface{}) (*CallResponse, error) {
	// TODO: send JSON-RPC tools/call, parse response
	_ = ctx
	_ = name
	_ = args
	return nil, nil
}
