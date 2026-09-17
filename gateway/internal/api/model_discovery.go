package api

import (
	"context"
	"crypto/tls"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/url"
	"sort"
	"strings"
	"time"
)

const maxModelCatalogBytes = 2 << 20

type discoverModelRequest struct {
	ID       string `json:"id" binding:"omitempty,max=86"`
	Provider string `json:"provider" binding:"required,oneof=openai anthropic openai_compatible ollama"`
	BaseURL  string `json:"base_url" binding:"omitempty,max=2048"`
	APIKey   string `json:"api_key" binding:"omitempty,max=8192"`
}

type discoveredModel struct {
	ID            string `json:"id"`
	Name          string `json:"name,omitempty"`
	OwnedBy       string `json:"owned_by,omitempty"`
	ContextWindow int64  `json:"context_window,omitempty"`
	Details       string `json:"details,omitempty"`
}

type modelCatalogPayload struct {
	Data []struct {
		ID            string `json:"id"`
		Name          string `json:"name"`
		DisplayName   string `json:"display_name"`
		OwnedBy       string `json:"owned_by"`
		ContextLength int64  `json:"context_length"`
		ContextWindow int64  `json:"context_window"`
	} `json:"data"`
	Models []struct {
		ID      string `json:"id"`
		Key     string `json:"key"`
		Name    string `json:"name"`
		Model   string `json:"model"`
		Details struct {
			Family            string `json:"family"`
			ParameterSize     string `json:"parameter_size"`
			QuantizationLevel string `json:"quantization_level"`
		} `json:"details"`
	} `json:"models"`
}

func normalizeModelBaseURL(provider, rawBaseURL string) string {
	baseURL := strings.TrimRight(strings.TrimSpace(rawBaseURL), "/")
	if provider != "openai_compatible" || baseURL == "" {
		return baseURL
	}
	endpoint, err := url.Parse(baseURL)
	if err != nil {
		return baseURL
	}
	if endpoint.Port() == "1234" && (endpoint.Path == "" || endpoint.Path == "/") {
		endpoint.Path = "/v1"
		return strings.TrimRight(endpoint.String(), "/")
	}
	return baseURL
}

func catalogURL(provider, rawBaseURL string) (*url.URL, error) {
	baseURL := strings.TrimSpace(rawBaseURL)
	if baseURL == "" {
		switch provider {
		case "openai":
			baseURL = "https://api.openai.com/v1"
		case "anthropic":
			baseURL = "https://api.anthropic.com/v1"
		case "ollama":
			baseURL = "http://127.0.0.1:11434"
		default:
			return nil, errors.New("OpenAI 兼容服务必须填写 Base URL")
		}
	}
	baseURL = normalizeModelBaseURL(provider, baseURL)
	endpoint, err := url.Parse(baseURL)
	if err != nil || endpoint.Scheme == "" || endpoint.Host == "" {
		return nil, errors.New("Base URL 不是有效的 HTTP(S) 地址")
	}
	if endpoint.Scheme != "http" && endpoint.Scheme != "https" {
		return nil, errors.New("Base URL 只支持 HTTP 或 HTTPS")
	}
	if endpoint.User != nil || endpoint.RawQuery != "" || endpoint.Fragment != "" {
		return nil, errors.New("Base URL 不能包含凭证、查询参数或片段")
	}
	path := strings.TrimRight(endpoint.Path, "/")
	if provider == "ollama" {
		switch {
		case strings.HasSuffix(path, "/api/tags"):
		case strings.HasSuffix(path, "/api"):
			path += "/tags"
		default:
			path += "/api/tags"
		}
	} else if !strings.HasSuffix(path, "/models") {
		path += "/models"
	}
	endpoint.Path = path
	return endpoint, nil
}

func modelDiscoveryClient() *http.Client {
	dialer := &net.Dialer{Timeout: 5 * time.Second, KeepAlive: 30 * time.Second}
	transport := &http.Transport{
		Proxy:                 nil,
		DialContext:           safeModelDiscoveryDial(dialer),
		ForceAttemptHTTP2:     true,
		MaxIdleConns:          10,
		IdleConnTimeout:       30 * time.Second,
		TLSHandshakeTimeout:   5 * time.Second,
		ResponseHeaderTimeout: 8 * time.Second,
		TLSClientConfig:       &tls.Config{MinVersion: tls.VersionTLS12},
	}
	return &http.Client{
		Transport: transport,
		Timeout:   10 * time.Second,
		CheckRedirect: func(_ *http.Request, _ []*http.Request) error {
			return errors.New("模型目录接口不允许重定向")
		},
	}
}

func safeModelDiscoveryDial(dialer *net.Dialer) func(context.Context, string, string) (net.Conn, error) {
	return func(ctx context.Context, network, address string) (net.Conn, error) {
		host, port, err := net.SplitHostPort(address)
		if err != nil {
			return nil, fmt.Errorf("解析模型服务地址失败: %w", err)
		}
		addresses, err := net.DefaultResolver.LookupIPAddr(ctx, host)
		if err != nil || len(addresses) == 0 {
			return nil, fmt.Errorf("无法解析模型服务地址 %q", host)
		}
		for _, address := range addresses {
			if unsafeDiscoveryIP(address.IP) {
				return nil, fmt.Errorf("模型服务地址 %q 指向受保护的网络范围", host)
			}
		}
		return dialer.DialContext(ctx, network, net.JoinHostPort(addresses[0].IP.String(), port))
	}
}

func unsafeDiscoveryIP(ip net.IP) bool {
	return ip.IsUnspecified() || ip.IsMulticast() || ip.IsLinkLocalUnicast() || ip.IsLinkLocalMulticast()
}

func discoverAvailableModels(
	ctx context.Context, provider, baseURL, apiKey string,
) ([]discoveredModel, error) {
	endpoint, err := catalogURL(provider, baseURL)
	if err != nil {
		return nil, err
	}
	request, err := http.NewRequestWithContext(ctx, http.MethodGet, endpoint.String(), nil)
	if err != nil {
		return nil, errors.New("无法创建模型目录请求")
	}
	request.Header.Set("Accept", "application/json")
	if apiKey != "" {
		if provider == "anthropic" {
			request.Header.Set("x-api-key", apiKey)
			request.Header.Set("anthropic-version", "2023-06-01")
		} else {
			request.Header.Set("Authorization", "Bearer "+apiKey)
		}
	}
	response, err := modelDiscoveryClient().Do(request)
	if err != nil {
		return nil, fmt.Errorf("无法连接模型目录: %w", err)
	}
	defer response.Body.Close()
	body, err := io.ReadAll(io.LimitReader(response.Body, maxModelCatalogBytes+1))
	if err != nil {
		return nil, errors.New("读取模型目录失败")
	}
	if len(body) > maxModelCatalogBytes {
		return nil, errors.New("模型目录响应过大")
	}
	if response.StatusCode < 200 || response.StatusCode >= 300 {
		return nil, fmt.Errorf("模型目录返回 HTTP %d", response.StatusCode)
	}
	var payload modelCatalogPayload
	if err := json.Unmarshal(body, &payload); err != nil {
		return nil, errors.New("模型目录没有返回可识别的 JSON")
	}
	models := make([]discoveredModel, 0, len(payload.Data)+len(payload.Models))
	seen := make(map[string]struct{})
	appendModel := func(model discoveredModel) {
		model.ID = strings.TrimSpace(model.ID)
		if model.ID == "" || len(model.ID) > 200 {
			return
		}
		if _, exists := seen[model.ID]; exists {
			return
		}
		seen[model.ID] = struct{}{}
		if model.Name == "" {
			model.Name = model.ID
		}
		models = append(models, model)
	}
	for _, item := range payload.Data {
		name := item.DisplayName
		if name == "" {
			name = item.Name
		}
		contextWindow := item.ContextWindow
		if contextWindow == 0 {
			contextWindow = item.ContextLength
		}
		appendModel(discoveredModel{
			ID: item.ID, Name: name, OwnedBy: item.OwnedBy, ContextWindow: contextWindow,
		})
	}
	for _, item := range payload.Models {
		id := item.ID
		if id == "" {
			id = item.Model
		}
		if id == "" {
			id = item.Key
		}
		if id == "" {
			id = item.Name
		}
		detailParts := make([]string, 0, 3)
		for _, part := range []string{item.Details.Family, item.Details.ParameterSize, item.Details.QuantizationLevel} {
			if part != "" {
				detailParts = append(detailParts, part)
			}
		}
		appendModel(discoveredModel{ID: id, Name: item.Name, Details: strings.Join(detailParts, " · ")})
	}
	if len(models) == 0 {
		return nil, errors.New("模型目录为空，或响应格式不受支持")
	}
	sort.SliceStable(models, func(i, j int) bool {
		return strings.ToLower(models[i].ID) < strings.ToLower(models[j].ID)
	})
	if len(models) > 500 {
		models = models[:500]
	}
	return models, nil
}
