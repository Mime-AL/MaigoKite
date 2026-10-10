package api

import (
	"bytes"
	"context"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	agentv1 "maigokite/gateway/pkg/proto/agent/v1"
)

type fakePhase2Client struct {
	lastSubject string
	lastMemory  *agentv1.Memory
}

func (f *fakePhase2Client) ListMemories(
	_ context.Context, workspaceID, subjectUserID, query string, _ int32,
) (*agentv1.MemoryList, error) {
	f.lastSubject = subjectUserID
	return &agentv1.MemoryList{Memories: []*agentv1.Memory{{
		Id: "memory_1", WorkspaceId: workspaceID, SubjectUserId: subjectUserID,
		Category: "preference", Content: "使用中文", SourceType: "user",
		Confidence: 1, CreatedAt: "now", UpdatedAt: "now",
	}}}, nil
}

func (f *fakePhase2Client) UpsertMemory(
	_ context.Context, workspaceID, subjectUserID string, memory *agentv1.Memory,
) (*agentv1.Memory, error) {
	f.lastSubject = subjectUserID
	memory.Id = "memory_created"
	memory.WorkspaceId = workspaceID
	memory.SubjectUserId = subjectUserID
	memory.SourceType = "user"
	f.lastMemory = memory
	return memory, nil
}

func (f *fakePhase2Client) DeleteMemory(context.Context, string, string, string) error {
	return nil
}

func (f *fakePhase2Client) GetWorkspaceDataSummary(context.Context, string) (*agentv1.WorkspaceDataSummary, error) {
	return &agentv1.WorkspaceDataSummary{StorageBackend: "sqlite", ConversationCount: 2, MemoryCount: 1}, nil
}

func (f *fakePhase2Client) ListMCPServers(context.Context, string) (*agentv1.MCPServerList, error) {
	return &agentv1.MCPServerList{Servers: []*agentv1.MCPServer{{
		Namespace: "fixture", Status: "running", Transport: "stdio", ToolNames: []string{"fixture__echo"},
	}}}, nil
}

func phase2TestRouter(client *fakePhase2Client) *gin.Engine {
	gin.SetMode(gin.TestMode)
	router := gin.New()
	group := router.Group("/workspaces/:workspaceID")
	group.Use(func(c *gin.Context) {
		c.Set("principal_id", "local-user")
		c.Next()
	})
	memory := &MemoryHandler{client: client}
	group.GET("/memories", memory.List)
	group.POST("/memories", memory.Create)
	group.GET("/data-summary", (&DataHandler{client: client}).Summary)
	group.GET("/mcp-servers", (&MCPRuntimeHandler{client: client}).List)
	return router
}

func TestPhase2MemoryEndpointsUseAuthenticatedSubject(t *testing.T) {
	client := &fakePhase2Client{}
	router := phase2TestRouter(client)

	list := httptest.NewRecorder()
	router.ServeHTTP(list, httptest.NewRequest(http.MethodGet, "/workspaces/personal/memories?q=中文", nil))
	if list.Code != http.StatusOK || client.lastSubject != "local-user" {
		t.Fatalf("unexpected memory list response: status=%d subject=%q body=%s", list.Code, client.lastSubject, list.Body.String())
	}

	created := httptest.NewRecorder()
	body := bytes.NewBufferString(`{"category":"preference","content":"使用中文","confidence":0.9}`)
	request := httptest.NewRequest(http.MethodPost, "/workspaces/personal/memories", body)
	request.Header.Set("Content-Type", "application/json")
	router.ServeHTTP(created, request)
	if created.Code != http.StatusCreated || client.lastMemory == nil || client.lastMemory.Confidence != 0.9 {
		t.Fatalf("unexpected memory create response: status=%d body=%s", created.Code, created.Body.String())
	}
}

func TestPhase2RuntimeInventoryResponses(t *testing.T) {
	client := &fakePhase2Client{}
	router := phase2TestRouter(client)

	for path, expected := range map[string]string{
		"/workspaces/personal/data-summary": `"storage_backend":"sqlite"`,
		"/workspaces/personal/mcp-servers":  `"namespace":"fixture"`,
	} {
		response := httptest.NewRecorder()
		router.ServeHTTP(response, httptest.NewRequest(http.MethodGet, path, nil))
		if response.Code != http.StatusOK || !bytes.Contains(response.Body.Bytes(), []byte(expected)) {
			t.Fatalf("unexpected response for %s: status=%d body=%s", path, response.Code, response.Body.String())
		}
	}
}
