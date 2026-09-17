package api

import (
	"bytes"
	"context"
	"errors"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strings"
	"time"
	"unicode/utf8"

	"github.com/gin-gonic/gin"
)

const (
	maxDirectoryEntries = 500
	maxPreviewBytes     = 512 * 1024
	maxDiffBytes        = 256 * 1024
	maxGitOutputBytes   = 4 * 1024 * 1024
)

var ignoredWorkspaceNames = map[string]bool{
	".git": true, ".venv": true, "node_modules": true, "__pycache__": true,
	"dist": true, "build": true, ".pytest_cache": true,
}

type WorkspaceHandler struct{ root string }

type workspaceEntry struct {
	Name       string `json:"name"`
	Path       string `json:"path"`
	Type       string `json:"type"`
	Size       int64  `json:"size,omitempty"`
	ModifiedAt string `json:"modified_at"`
}

type workspaceChange struct {
	Path          string `json:"path"`
	Status        string `json:"status"`
	Additions     int    `json:"additions"`
	Deletions     int    `json:"deletions"`
	Diff          string `json:"diff"`
	DiffTruncated bool   `json:"diff_truncated"`
}

type cappedBuffer struct {
	bytes.Buffer
	remaining int
}

func (buffer *cappedBuffer) Write(data []byte) (int, error) {
	written := len(data)
	if buffer.remaining > 0 {
		accepted := min(len(data), buffer.remaining)
		_, _ = buffer.Buffer.Write(data[:accepted])
		buffer.remaining -= accepted
	}
	return written, nil
}

func newWorkspaceHandler(root string) *WorkspaceHandler {
	if strings.TrimSpace(root) == "" {
		root = "."
	}
	abs, err := filepath.Abs(root)
	if err != nil {
		abs = root
	}
	if evaluated, err := filepath.EvalSymlinks(abs); err == nil {
		abs = evaluated
	}
	return &WorkspaceHandler{root: filepath.Clean(abs)}
}

func (h *WorkspaceHandler) resolve(relative string) (string, error) {
	target, err := h.resolveLexical(relative)
	if err != nil {
		return "", err
	}
	resolved, err := filepath.EvalSymlinks(target)
	if err != nil {
		return "", err
	}
	rel, err := filepath.Rel(h.root, resolved)
	if err != nil || rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) {
		return "", errors.New("symlink escapes the workspace")
	}
	return resolved, nil
}

func (h *WorkspaceHandler) resolveLexical(relative string) (string, error) {
	relative = filepath.FromSlash(strings.TrimSpace(relative))
	if filepath.IsAbs(relative) {
		return "", errors.New("workspace path must be relative")
	}
	target := filepath.Clean(filepath.Join(h.root, relative))
	rel, err := filepath.Rel(h.root, target)
	if err != nil || rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) {
		return "", errors.New("path escapes the workspace")
	}
	return target, nil
}

func (h *WorkspaceHandler) ListFiles(c *gin.Context) {
	target, err := h.resolve(c.Query("path"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "INVALID_PATH", "message": err.Error()}})
		return
	}
	items, err := os.ReadDir(target)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "NOT_DIRECTORY", "message": "path is not a readable directory"}})
		return
	}
	entries := make([]workspaceEntry, 0, min(len(items), maxDirectoryEntries))
	for _, item := range items {
		if len(entries) >= maxDirectoryEntries || ignoredWorkspaceNames[item.Name()] || item.Type()&os.ModeSymlink != 0 {
			continue
		}
		info, err := item.Info()
		if err != nil {
			continue
		}
		rel, err := filepath.Rel(h.root, filepath.Join(target, item.Name()))
		if err != nil {
			continue
		}
		kind := "file"
		if item.IsDir() {
			kind = "directory"
		}
		entries = append(entries, workspaceEntry{
			Name: item.Name(), Path: filepath.ToSlash(rel), Type: kind,
			Size: info.Size(), ModifiedAt: info.ModTime().UTC().Format(time.RFC3339),
		})
	}
	sort.SliceStable(entries, func(i, j int) bool {
		if entries[i].Type != entries[j].Type {
			return entries[i].Type == "directory"
		}
		return strings.ToLower(entries[i].Name) < strings.ToLower(entries[j].Name)
	})
	c.JSON(http.StatusOK, gin.H{"path": c.Query("path"), "entries": entries, "truncated": len(items) > maxDirectoryEntries})
}

func (h *WorkspaceHandler) ReadFile(c *gin.Context) {
	target, err := h.resolve(c.Query("path"))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "INVALID_PATH", "message": err.Error()}})
		return
	}
	info, err := os.Stat(target)
	if err != nil || !info.Mode().IsRegular() {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "NOT_FILE", "message": "path is not a readable file"}})
		return
	}
	file, err := os.Open(target)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": gin.H{"code": "READ_FAILED", "message": err.Error()}})
		return
	}
	defer file.Close()
	buffer, readErr := io.ReadAll(io.LimitReader(file, maxPreviewBytes+1))
	if readErr != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": gin.H{"code": "READ_FAILED", "message": readErr.Error()}})
		return
	}
	truncated := len(buffer) > maxPreviewBytes
	if truncated {
		buffer = buffer[:maxPreviewBytes]
	}
	binary := bytes.IndexByte(buffer, 0) >= 0 || !utf8.Valid(buffer)
	content := ""
	if !binary {
		content = string(buffer)
	}
	c.JSON(http.StatusOK, gin.H{
		"path": c.Query("path"), "content": content, "binary": binary,
		"truncated": truncated, "size": info.Size(), "modified_at": info.ModTime().UTC().Format(time.RFC3339),
	})
}

func (h *WorkspaceHandler) git(ctx context.Context, args ...string) ([]byte, error) {
	command := exec.CommandContext(ctx, "git", append([]string{"-C", h.root}, args...)...)
	command.Env = []string{"PATH=/usr/local/bin:/usr/bin:/bin", "LC_ALL=C"}
	output := &cappedBuffer{remaining: maxGitOutputBytes}
	command.Stdout = output
	command.Stderr = io.Discard
	err := command.Run()
	return output.Bytes(), err
}

func (h *WorkspaceHandler) Changes(c *gin.Context) {
	ctx, cancel := context.WithTimeout(c.Request.Context(), 8*time.Second)
	defer cancel()
	statusOutput, err := h.git(ctx, "status", "--porcelain=v1", "-z", "--untracked-files=normal")
	if err != nil {
		c.JSON(http.StatusOK, gin.H{"changes": []workspaceChange{}, "git": false, "truncated": false})
		return
	}
	parts := bytes.Split(statusOutput, []byte{0})
	changes := make([]workspaceChange, 0, min(len(parts), 200))
	changesTruncated := false
	for index := 0; index < len(parts); index++ {
		part := parts[index]
		if len(part) < 4 {
			continue
		}
		code := string(part[:2])
		path := string(part[3:])
		if (code[0] == 'R' || code[0] == 'C') && index+1 < len(parts) {
			index++
		}
		if _, err := h.resolveLexical(path); err != nil {
			continue
		}
		if len(changes) >= 200 {
			changesTruncated = true
			break
		}
		changes = append(changes, workspaceChange{
			Path: filepath.ToSlash(path), Status: changeStatus(code),
		})
	}
	c.JSON(http.StatusOK, gin.H{"changes": changes, "git": true, "truncated": changesTruncated})
}

func (h *WorkspaceHandler) ChangeDiff(c *gin.Context) {
	path := c.Query("path")
	if strings.TrimSpace(path) == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "INVALID_PATH", "message": "path is required"}})
		return
	}
	if _, err := h.resolveLexical(path); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": gin.H{"code": "INVALID_PATH", "message": err.Error()}})
		return
	}
	ctx, cancel := context.WithTimeout(c.Request.Context(), 5*time.Second)
	defer cancel()
	statusOutput, err := h.git(ctx, "status", "--porcelain=v1", "-z", "--untracked-files=normal", "--", path)
	parts := bytes.Split(statusOutput, []byte{0})
	if err != nil || len(parts) == 0 || len(parts[0]) < 4 {
		c.JSON(http.StatusNotFound, gin.H{"error": gin.H{"code": "CHANGE_NOT_FOUND", "message": "path has no workspace change"}})
		return
	}
	code := string(parts[0][:2])
	diff, truncated := h.fileDiff(ctx, code, path)
	additions, deletions := diffStats(diff)
	c.JSON(http.StatusOK, workspaceChange{
		Path: filepath.ToSlash(path), Status: changeStatus(code), Additions: additions,
		Deletions: deletions, Diff: diff, DiffTruncated: truncated,
	})
}

func (h *WorkspaceHandler) fileDiff(ctx context.Context, code, path string) (string, bool) {
	var output []byte
	if code != "??" {
		staged, _ := h.git(ctx, "diff", "--cached", "--no-ext-diff", "--unified=3", "--", path)
		unstaged, _ := h.git(ctx, "diff", "--no-ext-diff", "--unified=3", "--", path)
		output = append(staged, unstaged...)
	} else if target, err := h.resolve(path); err == nil {
		info, statErr := os.Stat(target)
		data, readErr := []byte(nil), statErr
		if statErr == nil && info.Size() <= maxDiffBytes {
			data, readErr = os.ReadFile(target)
		}
		if readErr == nil && utf8.Valid(data) && bytes.IndexByte(data, 0) < 0 {
			var builder strings.Builder
			builder.WriteString("--- /dev/null\n+++ b/" + filepath.ToSlash(path) + "\n")
			lines := strings.Split(string(data), "\n")
			lineCount := len(lines)
			if lineCount > 0 && lines[lineCount-1] == "" {
				lineCount--
			}
			builder.WriteString("@@ -0,0 +1," + itoa(lineCount) + " @@\n")
			for _, line := range lines[:lineCount] {
				builder.WriteString("+" + line + "\n")
			}
			output = []byte(builder.String())
		}
	}
	return truncateDiff(string(output), maxDiffBytes)
}

func truncateDiff(diff string, limit int) (string, bool) {
	if len(diff) <= limit {
		return diff, false
	}
	const marker = "\n… diff truncated …\n"
	if limit <= len(marker) {
		return "", true
	}
	prefix := diff[:limit-len(marker)]
	for len(prefix) > 0 && !utf8.ValidString(prefix) {
		prefix = prefix[:len(prefix)-1]
	}
	return prefix + marker, true
}

func changeStatus(code string) string {
	if code == "??" {
		return "untracked"
	}
	if strings.Contains(code, "D") {
		return "deleted"
	}
	if strings.ContainsAny(code, "RC") {
		return "renamed"
	}
	if strings.Contains(code, "A") {
		return "added"
	}
	return "modified"
}

func diffStats(diff string) (int, int) {
	additions, deletions := 0, 0
	for _, line := range strings.Split(diff, "\n") {
		if strings.HasPrefix(line, "+") && !strings.HasPrefix(line, "+++") {
			additions++
		} else if strings.HasPrefix(line, "-") && !strings.HasPrefix(line, "---") {
			deletions++
		}
	}
	return additions, deletions
}

func itoa(value int) string {
	if value == 0 {
		return "0"
	}
	digits := make([]byte, 0, 12)
	for value > 0 {
		digits = append(digits, byte('0'+value%10))
		value /= 10
	}
	for left, right := 0, len(digits)-1; left < right; left, right = left+1, right-1 {
		digits[left], digits[right] = digits[right], digits[left]
	}
	return string(digits)
}
