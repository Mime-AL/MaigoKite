package api

import (
	"context"
	"encoding/json"
	"log/slog"

	"google.golang.org/grpc/status"
	ws "maigokite/gateway/internal/websocket"
	agentv1 "maigokite/gateway/pkg/proto/agent/v1"
)

// The Core owns execution. This subscription survives the initiating HTTP
// request, and ends when the Core stream or the Gateway's client connection ends.
func forwardExecutionEvents(hub *ws.Hub, first *agentv1.AgentEvent, events <-chan *agentv1.AgentEvent, errs <-chan error, cancel context.CancelFunc) {
	broadcast := func(event *agentv1.AgentEvent) {
		if event.EventId == "" || event.Sequence <= 0 || event.OccurredAt == "" {
			// Transport errors are not durable product events. Never allocate a
			// competing sequence; reconnect fetches actual Core product facts.
			slog.Warn("Core stream returned an unpersisted event", "conversation_id", event.ConversationId,
				"event_type", event.Type)
			hub.Disconnect(event.ConversationId)
			return
		}
		payload := json.RawMessage(event.PayloadJson)
		if len(payload) == 0 || !json.Valid(payload) {
			payload, _ = json.Marshal(map[string]any{"content": event.Content, "message": event.Message, "code": event.Code, "retryable": event.Retryable})
		}
		hub.BroadcastPersistedEvent(event.ConversationId, event.TaskId, event.Type, payload, event.EventId, uint64(event.Sequence), event.OccurredAt)
	}
	broadcast(first)
	go func() {
		defer cancel()
		for event := range events {
			broadcast(event)
		}
		for err := range errs {
			if err != nil {
				// A broken subscription is not proof that execution failed.
				// Reconnect triggers the existing persisted-event catch-up.
				slog.Warn("Core event subscription ended", "conversation_id", first.ConversationId,
					"task_id", first.TaskId, "grpc_code", status.Code(err).String())
				hub.Disconnect(first.ConversationId)
			}
		}
	}()
}
