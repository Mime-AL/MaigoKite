package api

import (
	"errors"
	"os"
	"path/filepath"
	"strings"
	"unsafe"

	"golang.org/x/sys/windows"
)

func createWorkspaceEntry(root, parent, name, kind string) (os.FileInfo, error) {
	path, err := windows.UTF16PtrFromString(root)
	if err != nil {
		return nil, err
	}
	handle, err := windows.CreateFile(path, windows.FILE_GENERIC_READ,
		windows.FILE_SHARE_READ|windows.FILE_SHARE_WRITE|windows.FILE_SHARE_DELETE, nil, windows.OPEN_EXISTING,
		windows.FILE_FLAG_BACKUP_SEMANTICS|windows.FILE_FLAG_OPEN_REPARSE_POINT, 0)
	if err != nil {
		return nil, err
	}
	defer func() { _ = windows.CloseHandle(handle) }()
	checkDirectory := func(handle windows.Handle) error {
		var info windows.ByHandleFileInformation
		if err := windows.GetFileInformationByHandle(handle, &info); err != nil {
			return err
		}
		if info.FileAttributes&windows.FILE_ATTRIBUTE_REPARSE_POINT != 0 || info.FileAttributes&windows.FILE_ATTRIBUTE_DIRECTORY == 0 {
			return os.ErrPermission
		}
		return nil
	}
	if err := checkDirectory(handle); err != nil {
		return nil, err
	}
	openRelative := func(parent windows.Handle, component string, disposition, options, access uint32) (windows.Handle, error) {
		value, err := windows.NewNTUnicodeString(component)
		if err != nil {
			return 0, err
		}
		attributes := windows.OBJECT_ATTRIBUTES{RootDirectory: parent, ObjectName: value, Attributes: windows.OBJ_CASE_INSENSITIVE | windows.OBJ_DONT_REPARSE}
		attributes.Length = uint32(unsafe.Sizeof(attributes))
		var child windows.Handle
		var status windows.IO_STATUS_BLOCK
		err = windows.NtCreateFile(&child, access, &attributes, &status, nil, windows.FILE_ATTRIBUTE_NORMAL,
			windows.FILE_SHARE_READ|windows.FILE_SHARE_WRITE|windows.FILE_SHARE_DELETE, disposition,
			options|windows.FILE_OPEN_REPARSE_POINT|windows.FILE_SYNCHRONOUS_IO_NONALERT, 0, 0)
		var native windows.NTStatus
		if errors.As(err, &native) {
			err = native.Errno()
		}
		return child, err
	}
	for _, component := range strings.Split(filepath.Clean(parent), string(filepath.Separator)) {
		if component == "." || component == "" {
			continue
		}
		if component == ".." {
			return nil, os.ErrPermission
		}
		next, err := openRelative(handle, component, windows.FILE_OPEN, windows.FILE_DIRECTORY_FILE, windows.FILE_GENERIC_READ)
		if err != nil {
			return nil, err
		}
		_ = windows.CloseHandle(handle)
		handle = next
		if err := checkDirectory(handle); err != nil {
			return nil, err
		}
	}
	options := uint32(windows.FILE_NON_DIRECTORY_FILE)
	if kind == "directory" {
		options = windows.FILE_DIRECTORY_FILE
	}
	child, err := openRelative(handle, name, windows.FILE_CREATE, options, windows.FILE_GENERIC_READ|windows.FILE_GENERIC_WRITE)
	if err != nil {
		return nil, err
	}
	file := os.NewFile(uintptr(child), name)
	defer file.Close()
	return file.Stat()
}
