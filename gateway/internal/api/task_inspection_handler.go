package api

import (
	"encoding/json"
	"net/http"

	"github.com/gin-gonic/gin"
	agentgrpc "maigokite/gateway/internal/grpc"
	agentv1 "maigokite/gateway/pkg/proto/agent/v1"
)

type TaskInspectionHandler struct{ client *agentgrpc.AgentClient }

func (h *TaskInspectionHandler) Capabilities(c *gin.Context) {
	health, err := h.client.Health(c.Request.Context())
	if err != nil {
		grpcError(c, err)
		return
	}
	capabilities := health.Capabilities
	if capabilities == nil {
		capabilities = map[string]bool{}
	}
	c.JSON(http.StatusOK, gin.H{"capabilities": capabilities})
}

func (h *TaskInspectionHandler) Jobs(c *gin.Context) {
	items, err := h.client.ListJobs(c.Request.Context(), c.Param("workspaceID"), c.Query("conversation_id"))
	if err != nil {
		grpcError(c, err)
		return
	}
	jobs := make([]gin.H, 0, len(items.Jobs))
	for _, job := range items.Jobs {
		jobs = append(jobs, gin.H{"id": job.Id, "task_id": job.TaskId, "conversation_id": job.ConversationId,
			"command": job.Command, "status": job.Status, "log_tail": job.LogTail,
			"live": job.Live, "live_logs_available": job.LiveLogsAvailable, "stdin_available": job.StdinAvailable})
	}
	c.JSON(http.StatusOK, gin.H{"jobs": jobs})
}

func (h *TaskInspectionHandler) StopJob(c *gin.Context) {
	if err := h.client.StopJob(c.Request.Context(), c.Param("workspaceID"), c.Param("jobID"), c.GetString("principal_id")); err != nil {
		grpcError(c, err)
		return
	}
	c.Status(http.StatusNoContent)
}

func (h *TaskInspectionHandler) WriteJobInput(c *gin.Context) {
	c.Request.Body = http.MaxBytesReader(c.Writer, c.Request.Body, 32*1024)
	var req struct {
		Text string `json:"text"`
		EOF  bool   `json:"eof"`
	}
	if err := c.ShouldBindJSON(&req); err != nil || len(req.Text) > 4096 || (req.Text == "" && !req.EOF) {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "VALIDATION", "message": "输入须为 1–4096 字节，或关闭标准输入。"}})
		return
	}
	err := h.client.WriteJobInput(c.Request.Context(), &agentv1.JobInputRequest{
		WorkspaceId: c.Param("workspaceID"), JobId: c.Param("jobID"), PrincipalId: c.GetString("principal_id"),
		Text: req.Text, Eof: req.EOF,
	})
	if err != nil {
		grpcError(c, err)
		return
	}
	c.Status(http.StatusNoContent)
}

func (h *TaskInspectionHandler) Inputs(c *gin.Context) {
	items, err := h.client.ListTaskInputs(c.Request.Context(), c.Param("workspaceID"), c.Param("taskID"))
	if err != nil {
		grpcError(c, err)
		return
	}
	inputs := items.Inputs
	if inputs == nil {
		inputs = []*agentv1.TaskInput{}
	}
	c.JSON(http.StatusOK, gin.H{"inputs": inputs})
}

func (h *TaskInspectionHandler) SubmitInput(c *gin.Context) {
	var req struct {
		Content string `json:"content" binding:"required,max=10000"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "VALIDATION", "message": err.Error()}})
		return
	}
	key := c.GetHeader("Idempotency-Key")
	if key == "" || len(key) > 128 {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "VALIDATION", "message": "Idempotency-Key is required (up to 128 bytes)"}})
		return
	}
	item, err := h.client.SubmitTaskInput(c.Request.Context(), &agentv1.TaskInputRequest{
		WorkspaceId: c.Param("workspaceID"), TaskId: c.Param("taskID"), Content: req.Content, IdempotencyKey: key,
	})
	if err != nil {
		grpcError(c, err)
		return
	}
	c.JSON(http.StatusAccepted, item)
}

func toolCallValue(item *agentv1.ToolCall) gin.H {
	var arguments, result any
	_ = json.Unmarshal([]byte(item.ArgumentsJson), &arguments)
	_ = json.Unmarshal([]byte(item.ResultJson), &result)
	return gin.H{
		"id": item.Id, "task_id": item.TaskId, "tool_name": item.ToolName,
		"arguments": arguments, "result": result, "summary": item.Summary,
		"status": item.Status, "risk_level": item.RiskLevel,
		"created_at": item.CreatedAt, "updated_at": item.UpdatedAt,
	}
}

func (h *TaskInspectionHandler) Get(c *gin.Context) {
	item, err := h.client.GetTaskInspection(c.Request.Context(), c.Param("workspaceID"), c.Param("taskID"))
	if err != nil {
		grpcError(c, err)
		return
	}
	calls := make([]gin.H, 0, len(item.ToolCalls))
	for _, call := range item.ToolCalls {
		calls = append(calls, toolCallValue(call))
	}
	approvals := make([]approvalResponse, 0, len(item.Approvals))
	for _, approval := range item.Approvals {
		approvals = append(approvals, approvalValue(approval))
	}
	var projection map[string]any
	if err := json.Unmarshal([]byte(item.ProjectionJson), &projection); err != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": gin.H{"code": "INVALID_PROJECTION", "message": "invalid task projection"}})
		return
	}
	c.JSON(http.StatusOK, gin.H{
		"task": taskValue(item.Task), "tool_calls": calls, "approvals": approvals,
		"projection": projection, "last_sequence": item.LastSequence,
	})
}
