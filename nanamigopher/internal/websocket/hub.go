// Package websocket provides WebSocket connection management for real-time
// event streaming between the Go Gateway and frontend clients.
package websocket

import (
	"encoding/json"
	"sync"
	"time"
)

// Hub manages all WebSocket connections organized by session ID.
type Hub struct {
	// sessionID -> set of connected clients
	clients    map[string]map[*Client]bool
	register   chan *Client
	unregister chan *Client
	broadcast  chan *BroadcastMessage
	mu         sync.RWMutex
}

// Client represents a single WebSocket connection.
type Client struct {
	sessionID string
	conn      interface{} // *websocket.Conn (deferred import to avoid dependency)
	send      chan []byte
}

// BroadcastMessage carries a message to be sent to all clients in a session.
type BroadcastMessage struct {
	SessionID string
	Event     StreamEvent
}

// StreamEvent is the standardized event format pushed to the frontend.
type StreamEvent struct {
	Type      string          `json:"type"`       // step_start, step_complete, message_chunk, error
	Data      json.RawMessage `json:"data"`       // event-specific payload
	Timestamp int64           `json:"timestamp"`
}

// NewHub creates and returns a new Hub instance.
func NewHub() *Hub {
	return &Hub{
		clients:    make(map[string]map[*Client]bool),
		register:   make(chan *Client),
		unregister: make(chan *Client),
		broadcast:  make(chan *BroadcastMessage),
	}
}

// Run starts the Hub's main event loop.
func (h *Hub) Run() {
	for {
		select {
		case client := <-h.register:
			h.registerClient(client)
		case client := <-h.unregister:
			h.unregisterClient(client)
		case msg := <-h.broadcast:
			h.broadcastMessage(msg)
		}
	}
}

func (h *Hub) registerClient(client *Client) {
	h.mu.Lock()
	defer h.mu.Unlock()
	if h.clients[client.sessionID] == nil {
		h.clients[client.sessionID] = make(map[*Client]bool)
	}
	h.clients[client.sessionID][client] = true
}

func (h *Hub) unregisterClient(client *Client) {
	h.mu.Lock()
	defer h.mu.Unlock()
	if clients, ok := h.clients[client.sessionID]; ok {
		delete(clients, client)
		if len(clients) == 0 {
			delete(h.clients, client.sessionID)
		}
	}
	close(client.send)
}

func (h *Hub) broadcastMessage(msg *BroadcastMessage) {
	h.mu.RLock()
	defer h.mu.RUnlock()
	if clients, ok := h.clients[msg.SessionID]; ok {
		data, _ := json.Marshal(msg.Event)
		for client := range clients {
			select {
			case client.send <- data:
			default:
				close(client.send)
				delete(clients, client)
			}
		}
	}
}

// Register adds a new client to the hub.
func (h *Hub) Register(sessionID string) *Client {
	c := &Client{
		sessionID: sessionID,
		send:      make(chan []byte, 256),
	}
	h.register <- c
	return c
}

// Unregister removes a client from the hub.
func (h *Hub) Unregister(client *Client) {
	h.unregister <- client
}

// Broadcast sends an event to all clients in the given session.
func (h *Hub) Broadcast(sessionID string, eventType string, data json.RawMessage) {
	h.broadcast <- &BroadcastMessage{
		SessionID: sessionID,
		Event: StreamEvent{
			Type:      eventType,
			Data:      data,
			Timestamp: time.Now().UnixMilli(),
		},
	}
}
