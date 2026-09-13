// Package websocket provides Inspector-specific WebSocket handling.
package websocket

import (
	"encoding/json"
)

// InspectorWS manages WebSocket connections dedicated to the Inspector UI.
type InspectorWS struct {
	hub *Hub
}

// NewInspectorWS creates a new Inspector WebSocket manager.
func NewInspectorWS(hub *Hub) *InspectorWS {
	return &InspectorWS{hub: hub}
}

// InspectorEvent is the event type used by the Inspector WebSocket endpoint.
type InspectorEvent struct {
	Type string          `json:"type"` // card_update, timeline_node, card_action
	Data json.RawMessage `json:"data"`
}

// BroadcastCardUpdate pushes a card state change to Inspector clients.
func (w *InspectorWS) BroadcastCardUpdate(sessionID, title, status string, durationSec, tokenCount, toolCallCount int) {
	data, _ := json.Marshal(map[string]interface{}{
		"session_id":         sessionID,
		"title":              title,
		"status":             status,
		"running_duration_sec": durationSec,
		"token_count":        tokenCount,
		"tool_call_count":    toolCallCount,
	})
	w.hub.Broadcast(sessionID, "card_update", data)
}

// BroadcastTimelineNode pushes a new timeline node to Inspector clients.
func (w *InspectorWS) BroadcastTimelineNode(nodeID, nodeType, title, status string, durationMs int64, details map[string]interface{}) {
	data, _ := json.Marshal(map[string]interface{}{
		"node_id":    nodeID,
		"node_type":  nodeType,
		"title":      title,
		"status":     status,
		"duration_ms": durationMs,
		"details":    details,
	})
	w.hub.Broadcast(nodeID, "timeline_node", data)
}

// BroadcastCardAction notifies clients of a card action result.
func (w *InspectorWS) BroadcastCardAction(action, sessionID, result string) {
	data, _ := json.Marshal(map[string]interface{}{
		"action":     action,
		"session_id": sessionID,
		"result":     result,
	})
	w.hub.Broadcast(sessionID, "card_action", data)
}
