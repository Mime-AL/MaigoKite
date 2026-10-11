package api

import (
	"errors"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
)

func validEntryName(name string) bool {
	if name == "" || len(name) > 255 || name != strings.TrimSpace(name) ||
		name == "." || name == ".." || strings.EqualFold(name, ".git") ||
		strings.HasSuffix(name, ".") || strings.ContainsAny(name, "\\/:*?\"<>|") {
		return false
	}
	for _, character := range name {
		if character < 32 || character == 127 {
			return false
		}
	}
	base := strings.ToUpper(strings.SplitN(name, ".", 2)[0])
	if base == "CON" || base == "PRN" || base == "AUX" || base == "NUL" ||
		(len(base) == 4 && (base[:3] == "COM" || base[:3] == "LPT") && base[3] >= '1' && base[3] <= '9') {
		return false
	}
	return true
}

// Human-triggered creation is intentionally separate from Agent tool execution.
// The registered workspace, owner check and exclusive filesystem create bound it.
func (h *WorkspaceHandler) CreateEntry(c *gin.Context) {
	var request struct {
		Name string `json:"name" binding:"required"`
		Type string `json:"type" binding:"required,oneof=file directory"`
	}
	if c.ShouldBindJSON(&request) != nil || !validEntryName(request.Name) {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "INVALID_NAME", "message": "Choose a valid file or folder name."}})
		return
	}
	parent, err := h.resolve(c.Query("path"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "INVALID_PATH", "message": "The destination is not inside the workspace."}})
		return
	}
	relative, err := filepath.Rel(h.root, parent)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "INVALID_PATH", "message": "The destination is not inside the workspace."}})
		return
	}
	for _, component := range strings.Split(relative, string(filepath.Separator)) {
		if strings.EqualFold(component, ".git") {
			c.JSON(http.StatusForbidden, gin.H{"error": gin.H{"code": "ACCESS_DENIED", "message": "Git metadata cannot be changed here."}})
			return
		}
	}
	if c.Request.Context().Err() != nil {
		return
	}
	// Directory handles keep a swapped symlink/junction from redirecting creation.
	info, err := createWorkspaceEntry(h.root, relative, request.Name, request.Type)
	if err != nil {
		status, code, message := http.StatusInternalServerError, "CREATE_FAILED", "The entry could not be created."
		if errors.Is(err, os.ErrExist) {
			status, code, message = http.StatusConflict, "ALREADY_EXISTS", "A file or folder with this name already exists."
		} else if errors.Is(err, os.ErrPermission) {
			status, code, message = http.StatusForbidden, "ACCESS_DENIED", "The folder is not writable."
		}
		c.JSON(status, gin.H{"error": gin.H{"code": code, "message": message}})
		return
	}
	c.Header("Cache-Control", "no-store")
	c.JSON(http.StatusCreated, workspaceEntry{
		Name: request.Name, Path: filepath.ToSlash(filepath.Join(relative, request.Name)),
		Type: request.Type, Size: info.Size(), ModifiedAt: info.ModTime().UTC().Format(time.RFC3339),
	})
}

// Browser clients can request the host's file manager, never an arbitrary shell
// command or an unregistered absolute path. Desktop clients reuse Electron IPC.
func (h *WorkspaceHandler) OpenFolder(c *gin.Context) {
	host, _, err := net.SplitHostPort(c.Request.RemoteAddr)
	address := net.ParseIP(host)
	if err != nil || address == nil || !address.IsLoopback() {
		c.JSON(http.StatusForbidden, gin.H{"error": gin.H{"code": "LOCAL_ONLY", "message": "Folders can only be opened on the computer running the app."}})
		return
	}
	target, err := h.resolve(c.Query("path"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "INVALID_PATH", "message": "Choose a folder inside the workspace."}})
		return
	}
	info, err := os.Stat(target)
	if err != nil || !info.IsDir() {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "NOT_DIRECTORY", "message": "This location is not a folder."}})
		return
	}
	program := "xdg-open"
	if runtime.GOOS == "darwin" {
		program = "open"
	} else if runtime.GOOS == "windows" {
		program = "explorer.exe"
	}
	command := exec.Command(program, target)
	if err := command.Start(); err != nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"error": gin.H{"code": "OPEN_FAILED", "message": "The file manager could not be started."}})
		return
	}
	// Some desktop launchers stay alive with the window. Reap them without holding
	// the HTTP request open; a quick launcher failure is still reported inline.
	done := make(chan error, 1)
	go func() { done <- command.Wait() }()
	timer := time.NewTimer(300 * time.Millisecond)
	defer timer.Stop()
	select {
	case err := <-done:
		if err != nil {
			c.JSON(http.StatusServiceUnavailable, gin.H{"error": gin.H{"code": "OPEN_FAILED", "message": "The file manager could not open the folder."}})
			return
		}
		c.Status(http.StatusNoContent)
	case <-timer.C:
		c.JSON(http.StatusAccepted, gin.H{"launched": true})
	case <-c.Request.Context().Done():
		return
	}
}
