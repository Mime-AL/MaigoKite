package api

import (
	"github.com/gin-gonic/gin"
	agentgrpc "maigokite/gateway/internal/grpc"
	agentv1 "maigokite/gateway/pkg/proto/agent/v1"
	"net/http"
)

// Folder workspaces are personal resources, not another tenant/authentication model.
type WorkspaceFolderHandler struct{ client *agentgrpc.AgentClient }

func (h *WorkspaceFolderHandler) List(c *gin.Context) {
	folders, err := h.client.ListWorkspaceFolders(c.Request.Context(), c.Param("workspaceID"))
	if err != nil {
		grpcError(c, err)
		return
	}
	c.JSON(http.StatusOK, folders)
}

func (h *WorkspaceFolderHandler) Create(c *gin.Context) {
	var req struct {
		RootPath string `json:"root_path" binding:"required,max=4096"`
		Name     string `json:"name" binding:"max=120"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "VALIDATION", "message": err.Error()}})
		return
	}
	folder, err := h.client.CreateWorkspaceFolder(c.Request.Context(), &agentv1.WorkspaceFolderRequest{
		WorkspaceId: c.Param("workspaceID"), RootPath: req.RootPath, Name: req.Name,
	})
	if err != nil {
		grpcError(c, err)
		return
	}
	c.JSON(http.StatusCreated, folder)
}

func (h *WorkspaceFolderHandler) Delete(c *gin.Context) {
	err := h.client.DeleteWorkspaceFolder(c.Request.Context(), &agentv1.WorkspaceFolderDeleteRequest{
		WorkspaceId: c.Param("workspaceID"), FolderId: c.Param("folderID"), PrincipalId: c.GetString("principal_id"),
	})
	if err != nil {
		grpcError(c, err)
		return
	}
	c.Status(http.StatusNoContent)
}

// Resolve registered IDs in Core; never accept an arbitrary root in file-preview queries.
func (h *WorkspaceFolderHandler) Files(fallback *WorkspaceHandler, action func(*WorkspaceHandler, *gin.Context)) gin.HandlerFunc {
	return func(c *gin.Context) {
		folderID := c.Query("folder_id")
		handler := fallback
		if h.client != nil {
			folder, err := h.client.GetWorkspaceFolder(c.Request.Context(), c.Param("workspaceID"), folderID)
			if err != nil {
				grpcError(c, err)
				return
			}
			resolved := newWorkspaceHandler(folder.RootPath)
			if folderID != "" || resolved.root != fallback.root {
				handler = resolved
			}
		}
		action(handler, c)
	}
}
