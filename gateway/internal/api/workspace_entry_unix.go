//go:build !windows

package api

import (
	"os"
	"path/filepath"
	"strings"

	"golang.org/x/sys/unix"
)

// Reuse openat/mkdirat, anchored to directory descriptors, not a path-check/write
// sequence that could follow a symlink swapped by another process.
func createWorkspaceEntry(root, parent, name, kind string) (os.FileInfo, error) {
	flags := unix.O_RDONLY | unix.O_DIRECTORY | unix.O_NOFOLLOW | unix.O_CLOEXEC
	fd, err := unix.Open(root, flags, 0)
	if err != nil {
		return nil, err
	}
	defer func() { _ = unix.Close(fd) }()
	for _, component := range strings.Split(filepath.Clean(parent), string(filepath.Separator)) {
		if component == "." || component == "" {
			continue
		}
		if component == ".." {
			return nil, os.ErrPermission
		}
		next, err := unix.Openat(fd, component, flags, 0)
		if err != nil {
			return nil, err
		}
		_ = unix.Close(fd)
		fd = next
	}
	var child int
	if kind == "directory" {
		if err := unix.Mkdirat(fd, name, 0755); err != nil {
			return nil, err
		}
		child, err = unix.Openat(fd, name, flags, 0)
	} else {
		child, err = unix.Openat(fd, name, unix.O_WRONLY|unix.O_CREAT|unix.O_EXCL|unix.O_NOFOLLOW|unix.O_CLOEXEC, 0644)
	}
	if err != nil {
		return nil, err
	}
	file := os.NewFile(uintptr(child), name)
	defer file.Close()
	return file.Stat()
}
