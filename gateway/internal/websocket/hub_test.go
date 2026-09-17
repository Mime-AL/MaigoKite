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
