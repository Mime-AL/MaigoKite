package websocket

import (
	"encoding/json"
	"testing"
)

func TestBroadcastEnvelopeAndSequence(t *testing.T) {
	hub := NewHub()
	client := &Client{send: make(chan []byte, 2)}
	hub.clients["conv-1"] = map[*Client]struct{}{client: {}}
	hub.BroadcastEvent("conv-1", "task-1", "message.delta", json.RawMessage(`{"content":"hi"}`))
	hub.BroadcastEvent("conv-1", "task-1", "message.completed", json.RawMessage(`{}`))
	for expected := uint64(1); expected <= 2; expected++ {
		var event StreamEvent
		if err := json.Unmarshal(<-client.send, &event); err != nil {
			t.Fatal(err)
		}
		if event.SchemaVersion != 1 || event.Sequence != expected || event.ConversationID != "conv-1" {
			t.Fatalf("unexpected event: %+v", event)
		}
	}
}

func TestBroadcastPersistedEventPreservesJournalIdentity(t *testing.T) {
	hub := NewHub()
	client := &Client{send: make(chan []byte, 1)}
	hub.clients["conv-1"] = map[*Client]struct{}{client: {}}
	hub.BroadcastPersistedEvent(
		"conv-1", "task-1", "task.succeeded", json.RawMessage(`{}`),
		"event-stable", 42, "2026-09-18T00:00:00Z",
	)
	var event StreamEvent
	if err := json.Unmarshal(<-client.send, &event); err != nil {
		t.Fatal(err)
	}
	if event.EventID != "event-stable" || event.Sequence != 42 || event.OccurredAt != "2026-09-18T00:00:00Z" {
		t.Fatalf("persisted event metadata changed: %+v", event)
	}
}
