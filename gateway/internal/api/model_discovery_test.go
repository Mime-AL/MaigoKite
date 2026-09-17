package api

import (
	"context"
	"net"
	"net/http"
	"net/http/httptest"
	"testing"

	agentv1 "github.com/nanamigopher/nanamigopher/gateway/pkg/proto/agent/v1"
)

func TestDiscoverAvailableModelsFromOpenAICompatibleEndpoint(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/v1/models" {
			t.Fatalf("unexpected path: %s", r.URL.Path)
		}
		if r.Header.Get("Authorization") != "Bearer secret" {
			t.Fatal("API key was not sent as a bearer token")
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"data":[{"id":"model-b","name":"B"},{"id":"model-a","context_length":32768}]}`))
	}))
	defer server.Close()

	models, err := discoverAvailableModels(context.Background(), "openai_compatible", server.URL+"/v1", "secret")
	if err != nil {
		t.Fatal(err)
	}
	if len(models) != 2 || models[0].ID != "model-a" || models[0].ContextWindow != 32768 {
		t.Fatalf("unexpected models: %#v", models)
	}
}

func TestDiscoverAvailableModelsFromOllamaEndpoint(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/tags" {
			t.Fatalf("unexpected path: %s", r.URL.Path)
		}
		_, _ = w.Write([]byte(`{"models":[{"name":"qwen3:8b","details":{"family":"qwen3","parameter_size":"8B","quantization_level":"Q4_K_M"}}]}`))
	}))
	defer server.Close()

	models, err := discoverAvailableModels(context.Background(), "ollama", server.URL, "")
	if err != nil {
		t.Fatal(err)
	}
	if len(models) != 1 || models[0].ID != "qwen3:8b" || models[0].Details != "qwen3 · 8B · Q4_K_M" {
		t.Fatalf("unexpected models: %#v", models)
	}
}

func TestOfficialCatalogURLs(t *testing.T) {
	for _, testCase := range []struct {
		provider string
		want     string
	}{
		{provider: "openai", want: "https://api.openai.com/v1/models"},
		{provider: "anthropic", want: "https://api.anthropic.com/v1/models"},
		{provider: "ollama", want: "http://127.0.0.1:11434/api/tags"},
	} {
		endpoint, err := catalogURL(testCase.provider, "")
		if err != nil {
			t.Fatal(err)
		}
		if endpoint.String() != testCase.want {
			t.Fatalf("%s catalog URL = %s, want %s", testCase.provider, endpoint, testCase.want)
		}
	}
}

func TestLMStudioDefaultPortCatalogIncludesOpenAIV1Prefix(t *testing.T) {
	endpoint, err := catalogURL("openai_compatible", "http://127.0.0.1:1234")
	if err != nil {
		t.Fatal(err)
	}
	if endpoint.String() != "http://127.0.0.1:1234/v1/models" {
		t.Fatalf("LM Studio catalog URL = %s", endpoint)
	}
}

func TestModelDiscoveryRejectsProtectedNetworkRanges(t *testing.T) {
	for _, address := range []string{"0.0.0.0", "169.254.169.254", "fe80::1", "ff02::1"} {
		if !unsafeDiscoveryIP(net.ParseIP(address)) {
			t.Fatalf("expected %s to be rejected", address)
		}
	}
	for _, address := range []string{"127.0.0.1", "10.0.0.2", "8.8.8.8"} {
		if unsafeDiscoveryIP(net.ParseIP(address)) {
			t.Fatalf("expected %s to be allowed", address)
		}
	}
}

func TestStoredCredentialEndpointMustMatchDraft(t *testing.T) {
	saved := &agentv1.ChatModelSettings{
		Provider: "openai_compatible", BaseUrl: "https://models.example/v1/",
	}
	if !sameModelEndpoint(saved, "openai_compatible", "https://models.example/v1") {
		t.Fatal("equivalent endpoint should match")
	}
	if sameModelEndpoint(saved, "openai_compatible", "https://attacker.example/v1") {
		t.Fatal("a stored credential must not be reused for another endpoint")
	}
	if sameModelEndpoint(saved, "openai", "https://models.example/v1") {
		t.Fatal("a stored credential must not be reused for another provider")
	}
	lmStudio := &agentv1.ChatModelSettings{
		Provider: "openai_compatible", BaseUrl: "http://127.0.0.1:1234",
	}
	if !sameModelEndpoint(lmStudio, "openai_compatible", "http://127.0.0.1:1234/v1") {
		t.Fatal("legacy and canonical LM Studio endpoints should match")
	}
}
