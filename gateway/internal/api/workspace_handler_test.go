package api

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
	"unicode/utf8"

	"github.com/gin-gonic/gin"
)

func TestWorkspaceHandlerListsAndPreviewsFilesWithinRoot(t *testing.T) {
	gin.SetMode(gin.TestMode)
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "readme.txt"), []byte("hello"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.Mkdir(filepath.Join(root, ".git"), 0o700); err != nil {
		t.Fatal(err)
	}
	handler := newWorkspaceHandler(root)
	router := gin.New()
	router.GET("/files", handler.ListFiles)
	router.GET("/content", handler.ReadFile)

	response := httptest.NewRecorder()
	router.ServeHTTP(response, httptest.NewRequest(http.MethodGet, "/files", nil))
	if response.Code != http.StatusOK {
		t.Fatalf("list status = %d: %s", response.Code, response.Body.String())
	}
	var listing struct {
		Entries []workspaceEntry `json:"entries"`
	}
	if err := json.Unmarshal(response.Body.Bytes(), &listing); err != nil {
		t.Fatal(err)
	}
	if len(listing.Entries) != 1 || listing.Entries[0].Path != "readme.txt" {
		t.Fatalf("unexpected listing: %#v", listing.Entries)
	}

	response = httptest.NewRecorder()
	router.ServeHTTP(response, httptest.NewRequest(http.MethodGet, "/content?path=readme.txt", nil))
	if response.Code != http.StatusOK || !json.Valid(response.Body.Bytes()) {
		t.Fatalf("preview status = %d: %s", response.Code, response.Body.String())
	}
	if response.Body.String() == "" || !strings.Contains(response.Body.String(), "hello") {
		t.Fatalf("preview does not contain file content: %s", response.Body.String())
	}
}

func TestWorkspaceHandlerRejectsTraversalAndEscapingSymlink(t *testing.T) {
	root := t.TempDir()
	outside := t.TempDir()
	handler := newWorkspaceHandler(root)
	if _, err := handler.resolve("../outside"); err == nil {
		t.Fatal("expected traversal to be rejected")
	}
	if err := os.Symlink(outside, filepath.Join(root, "outside-link")); err == nil {
		if _, err := handler.resolve("outside-link"); err == nil {
			t.Fatal("expected escaping symlink to be rejected")
		}
	}
}

func TestWorkspaceChangesLoadDiffLazily(t *testing.T) {
	root := t.TempDir()
	if err := exec.Command("git", "init", "--quiet", root).Run(); err != nil {
		t.Skipf("git is unavailable: %v", err)
	}
	if err := os.WriteFile(filepath.Join(root, "readme.txt"), []byte("hello\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	handler := newWorkspaceHandler(root)
	router := gin.New()
	router.GET("/changes", handler.Changes)
	router.GET("/changes/diff", handler.ChangeDiff)

	response := httptest.NewRecorder()
	router.ServeHTTP(response, httptest.NewRequest(http.MethodGet, "/changes", nil))
	if response.Code != http.StatusOK {
		t.Fatalf("changes status = %d: %s", response.Code, response.Body.String())
	}
	var listing struct {
		Changes []workspaceChange `json:"changes"`
	}
	if err := json.Unmarshal(response.Body.Bytes(), &listing); err != nil {
		t.Fatal(err)
	}
	if len(listing.Changes) != 1 || listing.Changes[0].Diff != "" {
		t.Fatalf("expected one lazy change without a diff: %#v", listing.Changes)
	}

	response = httptest.NewRecorder()
	router.ServeHTTP(response, httptest.NewRequest(http.MethodGet, "/changes/diff?path=readme.txt", nil))
	if response.Code != http.StatusOK || !strings.Contains(response.Body.String(), "+hello") {
		t.Fatalf("diff status = %d: %s", response.Code, response.Body.String())
	}
}

func TestDiffStatsIgnoresHeaders(t *testing.T) {
	additions, deletions := diffStats("--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-old\n+new\n")
	if additions != 1 || deletions != 1 {
		t.Fatalf("stats = +%d -%d", additions, deletions)
	}
}

func TestTruncateDiffHonorsLimitAndUTF8(t *testing.T) {
	diff, truncated := truncateDiff(strings.Repeat("变更", maxDiffBytes), 128)
	if !truncated {
		t.Fatal("expected diff to be truncated")
	}
	if len(diff) > 128 {
		t.Fatalf("truncated diff size = %d", len(diff))
	}
	if !utf8.ValidString(diff) || !strings.Contains(diff, "diff truncated") {
		t.Fatalf("invalid truncated diff: %q", diff)
	}
}
