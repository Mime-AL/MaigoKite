package websocket

import (
	"encoding/json"
	"net"
	"net/http"
	"net/url"
	"sync"
	"sync/atomic"
	"time"

	gorilla "github.com/gorilla/websocket"
)

type StreamEvent struct {
	SchemaVersion  int             `json:"schema_version"`
	EventID        string          `json:"event_id"`
	Sequence       uint64          `json:"sequence"`
	Type           string          `json:"type"`
	OccurredAt     string          `json:"occurred_at"`
	ConversationID string          `json:"conversation_id,omitempty"`
	TaskID         string          `json:"task_id,omitempty"`
	Payload        json.RawMessage `json:"payload"`
}
type Client struct {
	conn *gorilla.Conn
	send chan []byte
}
type Hub struct {
	mu        sync.Mutex
	clients   map[string]map[*Client]struct{}
	sequences map[string]*atomic.Uint64
}

func NewHub() *Hub {
	return &Hub{clients: map[string]map[*Client]struct{}{}, sequences: map[string]*atomic.Uint64{}}
}
func (h *Hub) Run() {}

var upgrader = gorilla.Upgrader{CheckOrigin: func(r *http.Request) bool {
	origin := r.Header.Get("Origin")
	if origin == "" {
		return true
	}
	remoteHost, _, _ := net.SplitHostPort(r.RemoteAddr)
	if origin == "null" && net.ParseIP(remoteHost) != nil && net.ParseIP(remoteHost).IsLoopback() {
		return true
	}
	parsed, err := url.Parse(origin)
	if err != nil {
		return false
	}
	if parsed.Host == r.Host {
		return true
	}
	originHost := parsed.Hostname()
	return net.ParseIP(remoteHost) != nil && net.ParseIP(remoteHost).IsLoopback() && (originHost == "localhost" || (net.ParseIP(originHost) != nil && net.ParseIP(originHost).IsLoopback()))
}}

func (h *Hub) ServeWS(w http.ResponseWriter, r *http.Request, conversationID string) error {
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		return err
	}
	client := &Client{conn: conn, send: make(chan []byte, 64)}
	h.mu.Lock()
	if h.clients[conversationID] == nil {
		h.clients[conversationID] = map[*Client]struct{}{}
	}
	h.clients[conversationID][client] = struct{}{}
	h.mu.Unlock()
	go func() {
		for data := range client.send {
			if err := conn.WriteMessage(gorilla.TextMessage, data); err != nil {
				h.remove(conversationID, client)
				return
			}
		}
	}()
	go func() {
		for {
			if _, _, err := conn.ReadMessage(); err != nil {
				h.remove(conversationID, client)
				return
			}
		}
	}()
	return nil
}
func (h *Hub) remove(id string, c *Client) {
	h.mu.Lock()
	defer h.mu.Unlock()
	clients := h.clients[id]
	if _, ok := clients[c]; ok {
		delete(clients, c)
		close(c.send)
		_ = c.conn.Close()
	}
	if len(clients) == 0 {
		delete(h.clients, id)
	}
}
func (h *Hub) Broadcast(conversationID, eventType string, data json.RawMessage) {
	h.BroadcastEvent(conversationID, "", eventType, data)
}
func (h *Hub) BroadcastEvent(conversationID, taskID, eventType string, data json.RawMessage) {
	h.BroadcastPersistedEvent(conversationID, taskID, eventType, data, "", 0, "")
}
func (h *Hub) BroadcastPersistedEvent(conversationID, taskID, eventType string, data json.RawMessage, eventID string, sequence uint64, occurredAt string) {
	h.mu.Lock()
	defer h.mu.Unlock()
	counter := h.sequences[conversationID]
	if counter == nil {
		counter = &atomic.Uint64{}
		h.sequences[conversationID] = counter
	}
	seq := sequence
	if seq == 0 {
		seq = counter.Add(1)
	} else if seq > counter.Load() {
		counter.Store(seq)
	}
	if eventID == "" {
		eventID = conversationID + "-" + time.Now().UTC().Format("20060102150405.000000000")
	}
	if occurredAt == "" {
		occurredAt = time.Now().UTC().Format(time.RFC3339Nano)
	}
	event := StreamEvent{SchemaVersion: 1, EventID: eventID, Sequence: seq, Type: eventType, OccurredAt: occurredAt, ConversationID: conversationID, TaskID: taskID, Payload: data}
	encoded, _ := json.Marshal(event)
	for client := range h.clients[conversationID] {
		select {
		case client.send <- encoded:
		default:
			delete(h.clients[conversationID], client)
			close(client.send)
			_ = client.conn.Close()
		}
	}
}
