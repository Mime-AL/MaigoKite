// Package security provides audit logging for security events.
package security

import "time"

// AuditEntry records a security-relevant event.
type AuditEntry struct {
	Timestamp  time.Time `json:"timestamp"`
	Event      string    `json:"event"`       // injection_blocked, length_truncated, whitelist_hit
	Severity   string    `json:"severity"`    // block, warn, info
	Pattern    string    `json:"pattern,omitempty"`
	InputHash  string    `json:"input_hash,omitempty"`
}

// AuditLogger records security events to a log file or external service.
type AuditLogger struct {
	enabled     bool
	path        string
	retentionDays int
	maskInput   bool
}

// NewAuditLogger creates a new audit logger.
func NewAuditLogger(enabled bool, path string, retentionDays int, maskInput bool) *AuditLogger {
	return &AuditLogger{
		enabled:     enabled,
		path:        path,
		retentionDays: retentionDays,
		maskInput:   maskInput,
	}
}

// Log records a security event.
func (l *AuditLogger) Log(entry AuditEntry) {
	if !l.enabled {
		return
	}
	// TODO: write to audit log file or external service
	_ = entry
}
