// Package observability provides distributed tracing support.
package observability

import (
	"context"
)

// Tracer provides OpenTelemetry-compatible tracing.
// Phase 1 uses a no-op implementation; Phase 3 integrates with Langfuse.
type Tracer struct {
	enabled bool
	// TODO: add OTel tracer provider reference
}

// NewTracer creates a new tracer instance.
func NewTracer(enabled bool) *Tracer {
	return &Tracer{enabled: enabled}
}

// StartSpan begins a new trace span.
func (t *Tracer) StartSpan(ctx context.Context, name string) (context.Context, Span) {
	if !t.enabled {
		return ctx, &noopSpan{}
	}
	// TODO: create real OTel span
	return ctx, &noopSpan{name: name}
}

// Span represents a single trace span.
type Span interface {
	End()
	SetAttribute(key string, value interface{})
}

type noopSpan struct {
	name string
}

func (s *noopSpan) End()                        {}
func (s *noopSpan) SetAttribute(string, interface{}) {}
