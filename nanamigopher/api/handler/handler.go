// Package handler contains HTTP handler type aliases for external references.
// Handlers are defined in internal/api; this package provides compatibility
// for any external code that imports api/handler.
package handler

import "nanamigopher/internal/api"

// SessionHandler is an alias for internal/api.SessionHandler.
type SessionHandler = api.SessionHandler

// MessageHandler is an alias for internal/api.MessageHandler.
type MessageHandler = api.MessageHandler

// MemoryHandler is an alias for internal/api.MemoryHandler.
type MemoryHandler = api.MemoryHandler

// SkillHandler is an alias for internal/api.SkillHandler.
type SkillHandler = api.SkillHandler

// PermissionHandler is an alias for internal/api.PermissionHandler.
type PermissionHandler = api.PermissionHandler

// CredentialHandler is an alias for internal/api.CredentialHandler.
type CredentialHandler = api.CredentialHandler

// InspectorHandler is an alias for internal/api.InspectorHandler.
type InspectorHandler = api.InspectorHandler

// ApprovalHandler is an alias for internal/api.ApprovalHandler.
type ApprovalHandler = api.ApprovalHandler
