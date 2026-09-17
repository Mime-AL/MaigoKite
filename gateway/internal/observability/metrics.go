// Package observability provides metrics collection.
package observability

import "sync"

// MetricsCollector gathers application metrics.
type MetricsCollector struct {
	mu    sync.RWMutex
	metrics map[string]float64
}

// NewMetricsCollector creates a new metrics collector.
func NewMetricsCollector() *MetricsCollector {
	return &MetricsCollector{
		metrics: make(map[string]float64),
	}
}

// Set records a metric value.
func (m *MetricsCollector) Set(name string, value float64) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.metrics[name] = value
}

// Get retrieves a metric value.
func (m *MetricsCollector) Get(name string) float64 {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.metrics[name]
}

// Snapshot returns a copy of all current metrics.
func (m *MetricsCollector) Snapshot() map[string]float64 {
	m.mu.RLock()
	defer m.mu.RUnlock()
	cp := make(map[string]float64, len(m.metrics))
	for k, v := range m.metrics {
		cp[k] = v
	}
	return cp
}
