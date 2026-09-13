// Package websocket provides message broadcasting utilities for the Hub.
package websocket

import (
	"encoding/json"
)

// Broadcaster wraps the Hub and provides higher-level broadcast helpers.
type Broadcaster struct {
	hub *Hub
}

// NewBroadcaster creates a new Broadcaster tied to the given Hub.
func NewBroadcaster(hub *Hub) *Broadcaster {
	return &Broadcaster{hub: hub}
}

// BroadcastStepStart notifies all clients that a new step has begun.
func (b *Broadcaster) BroadcastStepStart(sessionID, step string) {
	data, _ := json.Marshal(map[string]interface{}{
		"step":   step,
		"status": "running",
	})
	b.hub.Broadcast(sessionID, "step_start", data)
}

// BroadcastStepComplete notifies all clients that a step has finished.
func (b *Broadcaster) BroadcastStepComplete(sessionID, step string, status string) {
	data, _ := json.Marshal(map[string]interface{}{
		"step":   step,
		"status": status,
	})
	b.hub.Broadcast(sessionID, "step_complete", data)
}

// BroadcastMessageChunk streams a text fragment to all clients.
func (b *Broadcaster) BroadcastMessageChunk(sessionID, content string) {
	data, _ := json.Marshal(map[string]interface{}{
		"content": content,
	})
	b.hub.Broadcast(sessionID, "message_chunk", data)
}

// BroadcastError sends an error event to all clients.
func (b *Broadcaster) BroadcastError(sessionID, level, code, message, suggestion string) {
	data, _ := json.Marshal(map[string]interface{}{
		"level":      level,
		"code":       code,
		"message":    message,
		"suggestion": suggestion,
	})
	b.hub.Broadcast(sessionID, "error", data)
}
