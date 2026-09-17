package config

import "testing"

func TestEnvironmentPortOverrides(t *testing.T) {
	t.Setenv("NG_HTTP_PORT", "9090")
	t.Setenv("NG_GRPC_PORT", "9091")
	t.Setenv("NANAMI_WORKSPACE_ROOT", "/tmp/nanami-workspace")
	cfg, err := Load("")
	if err != nil {
		t.Fatal(err)
	}
	if cfg.HTTP.Port != 9090 || cfg.GRPC.Port != 9091 {
		t.Fatalf("unexpected ports: http=%d grpc=%d", cfg.HTTP.Port, cfg.GRPC.Port)
	}
	if cfg.Workspace.Root != "/tmp/nanami-workspace" {
		t.Fatalf("unexpected workspace root: %s", cfg.Workspace.Root)
	}
}
