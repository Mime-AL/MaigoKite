package api

import (
	"io"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"strings"

	"github.com/gin-gonic/gin"
)

type folderBrowserEntry struct {
	Name string `json:"name"`
	Path string `json:"path"`
}

// Browse is an explicit local-owner folder picker, not a workspace file-preview
// escape hatch. It returns directory names only; registering a chosen path still
// goes through Core's existing CreateWorkspaceFolder validation.
func (h *WorkspaceFolderHandler) Browse(c *gin.Context) {
	host, _, err := net.SplitHostPort(c.Request.RemoteAddr)
	address := net.ParseIP(host)
	if err != nil || address == nil || !address.IsLoopback() {
		c.JSON(http.StatusForbidden, gin.H{"error": gin.H{"code": "LOCAL_ONLY", "message": "Folder browsing is only available on the computer running the app."}})
		return
	}
	c.Header("Cache-Control", "no-store")
	home, _ := os.UserHomeDir()
	if resolved, err := filepath.EvalSymlinks(home); err == nil {
		home = resolved
	}
	target := strings.TrimSpace(c.Query("path"))
	if target == "" {
		target = home
	}
	if len(target) > 4096 || strings.ContainsRune(target, '\x00') || !filepath.IsAbs(target) {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "INVALID_PATH", "message": "Choose a valid folder location."}})
		return
	}
	target, err = filepath.EvalSymlinks(filepath.Clean(target))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "NOT_DIRECTORY", "message": "The folder does not exist or cannot be opened."}})
		return
	}
	info, err := os.Stat(target)
	if err != nil || !info.IsDir() {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "NOT_DIRECTORY", "message": "The folder does not exist or cannot be opened."}})
		return
	}
	directory, err := os.Open(target)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "NOT_DIRECTORY", "message": "The folder does not exist or cannot be opened."}})
		return
	}
	defer directory.Close()
	info, err = directory.Stat()
	if err != nil || !info.IsDir() {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "NOT_DIRECTORY", "message": "The folder does not exist or cannot be opened."}})
		return
	}
	entries := make([]folderBrowserEntry, 0)
	truncated, scanned := false, 0
	showHidden := c.Query("show_hidden") == "true"
	// Bound both the response and work done in very large directories. ReadDir
	// batches avoid loading an entire drive into memory or following file contents.
	for {
		if c.Request.Context().Err() != nil {
			return
		}
		batch, readErr := directory.ReadDir(128)
		if readErr != nil && readErr != io.EOF {
			c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "READ_FAILED", "message": "The folder contents could not be read."}})
			return
		}
		for _, item := range batch {
			scanned++
			if scanned > 5000 {
				truncated = true
				break
			}
			if !showHidden && strings.HasPrefix(item.Name(), ".") {
				continue
			}
			path := filepath.Join(target, item.Name())
			isDirectory := item.IsDir()
			if item.Type()&os.ModeSymlink != 0 {
				if linked, err := os.Stat(path); err == nil {
					isDirectory = linked.IsDir()
				}
			}
			if !isDirectory {
				continue
			}
			if len(entries) == maxDirectoryEntries {
				truncated = true
				break
			}
			entries = append(entries, folderBrowserEntry{Name: item.Name(), Path: path})
		}
		if truncated || readErr == io.EOF {
			break
		}
	}
	parent := filepath.Dir(target)
	if parent == target {
		parent = ""
	}
	c.JSON(http.StatusOK, gin.H{
		"path": target, "parent": parent, "home": home,
		"root": filepath.VolumeName(target) + string(filepath.Separator),
		"entries": entries, "truncated": truncated,
	})
}
