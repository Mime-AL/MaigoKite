// Package api provides HTTP handler for memory management.
package api

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

// MemoryHandler handles memory CRUD and search operations.
type MemoryHandler struct{}

// ListResponse represents paginated memory list response.
type ListResponse struct {
	Memories []MemoryItem `json:"memories"`
	Total    int          `json:"total"`
	Page     int          `json:"page"`
	PerPage  int          `json:"per_page"`
}

// MemoryItem represents a single memory entry.
type MemoryItem struct {
	ID              string   `json:"id"`
	Type            string   `json:"type"` // preference, fact, summary
	Content         string   `json:"content"`
	Tags            []string `json:"tags"`
	ImportanceScore float64  `json:"importance_score"`
	IsPinned        bool     `json:"is_pinned"`
	CreatedAt       string   `json:"created_at"`
}

// List returns all memories with optional filtering.
func (h *MemoryHandler) List(c *gin.Context) {
	// TODO: query memory store
	c.JSON(http.StatusOK, ListResponse{})
}

// SearchRequest represents a memory search request.
type SearchRequest struct {
	Query          string   `json:"query" binding:"required"`
	Type           string   `json:"type"`
	Tags           []string `json:"tags"`
	TopK           int      `json:"top_k"`
	UseVectorSearch bool     `json:"use_vector_search"`
}

// Search performs semantic or keyword search on memories.
func (h *MemoryHandler) Search(c *gin.Context) {
	var req SearchRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	// TODO: forward to Python Agent via gRPC
	c.JSON(http.StatusOK, gin.H{"results": []interface{}{}})
}

// MemoryUpdateRequest represents a memory update request.
type MemoryUpdateRequest struct {
	Content  string   `json:"content"`
	Tags     []string `json:"tags"`
	IsPinned *bool    `json:"is_pinned"`
}

// Update modifies an existing memory entry.
func (h *MemoryHandler) Update(c *gin.Context) {
	id := c.Param("id")
	var req MemoryUpdateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	// TODO: forward to Python Agent via gRPC
	c.JSON(http.StatusOK, gin.H{"id": id, "updated_at": "now"})
}

// BatchDeleteRequest represents a batch deletion request.
type BatchDeleteRequest struct {
	IDs []string `json:"ids" binding:"required"`
}

// BatchDelete removes multiple memory entries.
func (h *MemoryHandler) BatchDelete(c *gin.Context) {
	var req BatchDeleteRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	// TODO: forward to Python Agent via gRPC
	c.JSON(http.StatusOK, gin.H{"deleted_count": len(req.IDs)})
}
