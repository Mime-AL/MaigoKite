package api

import (
	"bytes"
	"context"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	agentv1 "github.com/nanamigopher/nanamigopher/gateway/pkg/proto/agent/v1"
)

type fakeTaskClient struct {
	after int64
}

func (f *fakeTaskClient) GetTask(context.Context, string, string) (*agentv1.Task, error) {
	return &agentv1.Task{Id: "task-1", WorkspaceId: "personal", ConversationId: "conv-1", Status: "running"}, nil
}

func (f *fakeTaskClient) ListTasks(context.Context, string, string, int32) (*agentv1.TaskList, error) {
	item, _ := f.GetTask(context.Background(), "personal", "task-1")
	return &agentv1.TaskList{Tasks: []*agentv1.Task{item}}, nil
}

func (f *fakeTaskClient) CancelTask(context.Context, string, string) (*agentv1.Task, error) {
	return &agentv1.Task{Id: "task-1", WorkspaceId: "personal", ConversationId: "conv-1", Status: "cancelled"}, nil
}

func (f *fakeTaskClient) ListTaskEvents(_ context.Context, _, _ string, after int64, _ int32) (*agentv1.TaskEventList, error) {
	f.after = after
	return &agentv1.TaskEventList{Events: []*agentv1.TaskEvent{{
		Id: "event-2", WorkspaceId: "personal", ConversationId: "conv-1", TaskId: "task-1",
		Sequence: 2, EventType: "tool.completed", PayloadJson: `{"tool_name":"browser"}`,
		OccurredAt: "2026-09-18T00:00:00Z",
	}}}, nil
}

func (f *fakeTaskClient) ListSkills(context.Context, string) (*agentv1.SkillList, error) {
	return &agentv1.SkillList{Skills: []*agentv1.Skill{{
		Name: "research", Version: "1.0.0", Description: "Research workflow",
		Kind: "instruction", SourcePath: "skills/research/SKILL.md", ParametersSchemaJson: `{}`,
	}}}, nil
}

func taskTestRouter(client *fakeTaskClient) *gin.Engine {
	gin.SetMode(gin.TestMode)
	router := gin.New()
	group := router.Group("/workspaces/:workspaceID")
	tasks := &TaskHandler{client: client}
	group.GET("/tasks", tasks.List)
	group.GET("/tasks/:taskID", tasks.Get)
	group.POST("/tasks/:taskID/cancel", tasks.Cancel)
	group.GET("/conversations/:conversationID/events/history", tasks.Events)
	group.GET("/skills", (&SkillHandler{client: client}).List)
	return router
}

func TestTaskAndSkillEndpointsExposeDurableRuntimeState(t *testing.T) {
	client := &fakeTaskClient{}
	router := taskTestRouter(client)
	cases := map[string]string{
		"/workspaces/personal/tasks?conversation_id=conv-1":                `"status":"running"`,
		"/workspaces/personal/tasks/task-1":                                `"id":"task-1"`,
		"/workspaces/personal/conversations/conv-1/events/history?after=1": `"sequence":2`,
		"/workspaces/personal/skills":                                      `"name":"research"`,
	}
	for path, expected := range cases {
		response := httptest.NewRecorder()
		router.ServeHTTP(response, httptest.NewRequest(http.MethodGet, path, nil))
		if response.Code != http.StatusOK || !bytes.Contains(response.Body.Bytes(), []byte(expected)) {
			t.Fatalf("unexpected response for %s: status=%d body=%s", path, response.Code, response.Body.String())
		}
	}
	if client.after != 1 {
		t.Fatalf("expected history cursor 1, got %d", client.after)
	}

	cancelled := httptest.NewRecorder()
	router.ServeHTTP(cancelled, httptest.NewRequest(http.MethodPost, "/workspaces/personal/tasks/task-1/cancel", nil))
	if cancelled.Code != http.StatusOK || !bytes.Contains(cancelled.Body.Bytes(), []byte(`"status":"cancelled"`)) {
		t.Fatalf("unexpected cancel response: status=%d body=%s", cancelled.Code, cancelled.Body.String())
	}
}

func TestTaskHistoryRejectsInvalidCursor(t *testing.T) {
	router := taskTestRouter(&fakeTaskClient{})
	response := httptest.NewRecorder()
	router.ServeHTTP(response, httptest.NewRequest(
		http.MethodGet, "/workspaces/personal/conversations/conv-1/events/history?after=-1", nil,
	))
	if response.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d: %s", response.Code, response.Body.String())
	}
}
