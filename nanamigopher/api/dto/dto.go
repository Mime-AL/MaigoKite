// Package dto provides Data Transfer Object type aliases.
// DTOs are defined inline within handler files; this package offers
// a centralized location for shared types.
package dto

// StreamEvent represents a real-time event pushed to the frontend.
type StreamEvent struct {
	Type      string          `json:"type"`
	Data      map[string]interface{} `json:"data"`
	Timestamp int64          `json:"timestamp"`
}

// PaginatedResponse wraps a paginated list result.
type PaginatedResponse struct {
	Items     interface{} `json:"items"`
	Total     int         `json:"total"`
	Page      int         `json:"page"`
	PerPage   int         `json:"per_page"`
}

// ErrorResponse represents a standardized error response.
type ErrorResponse struct {
	Error    string `json:"error"`
	Message  string `json:"message"`
	Code     string `json:"code,omitempty"`
	Retryable bool  `json:"retryable,omitempty"`
}
