// Package observability provides Phase 1 console-based observability.
package observability

import (
	"fmt"
	"time"
)

// ConsoleObserver implements IObservability by printing to stdout.
type ConsoleObserver struct {
	prefix string
}

// NewConsoleObserver creates a console observer for logging and tracing.
func NewConsoleObserver(prefix string) ConsoleObserver {
	if prefix == "" {
		prefix = "MaigoKite"
	}
	return ConsoleObserver{prefix: prefix}
}

// Log writes a log message with the given level.
func (o ConsoleObserver) Log(level, message string) {
	timestamp := time.Now().Format(time.RFC3339)
	fmt.Printf("[%s] %s %s: %s\n", timestamp, o.prefix, level, message)
}

// Trace creates a new trace span for tracking operation duration.
func (o ConsoleObserver) Trace(operation string) TraceSpan {
	return TraceSpan{
		operation: operation,
		start:     time.Now(),
		observer:  o,
	}
}

// TraceSpan tracks the duration of an operation.
type TraceSpan struct {
	operation string
	start     time.Time
	observer  ConsoleObserver
}

// End marks the span as complete and logs the duration.
func (s TraceSpan) End() {
	duration := time.Since(s.start)
	s.observer.Log("TRACE", fmt.Sprintf("%s completed in %v", s.operation, duration))
}

// Metric records a numeric metric value.
func (o ConsoleObserver) Metric(name string, value float64) {
	o.Log("METRIC", fmt.Sprintf("%s = %.2f", name, value))
}
