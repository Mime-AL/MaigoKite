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

type modelCatalogEntry struct {
	ID                 string `json:"id"`
	Key                string `json:"key"`
	Model              string `json:"model"`
	Name               string `json:"name"`
	DisplayName        string `json:"display_name"`
	OwnedBy            string `json:"owned_by"`
	ContextLength      int64  `json:"context_length"`
	ContextWindow      int64  `json:"context_window"`
	ContextWindowCamel int64  `json:"contextWindow"`
	Details            struct {
		Family            string `json:"family"`
		ParameterSize     string `json:"parameter_size"`
		QuantizationLevel string `json:"quantization_level"`
	} `json:"details"`
}

type modelCatalogPayload struct {
	Data    []modelCatalogEntry `json:"data"`
	Models  json.RawMessage     `json:"models"`
	HasMore bool                `json:"has_more"`
	LastID  string              `json:"last_id"`
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
		// Anthropic accepts an API root or a root already ending in /v1.
		if provider == "anthropic" && !strings.HasSuffix(path, "/v1") {
			path += "/v1"
		}
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
	ctx, cancel := context.WithTimeout(ctx, 20*time.Second)
	defer cancel()
	client := modelDiscoveryClient()
	defer client.CloseIdleConnections()
	models := make([]discoveredModel, 0)
	seen := make(map[string]struct{})
	cursors := make(map[string]struct{})
	remainingBytes := maxModelCatalogBytes
	if provider == "anthropic" {
		query := endpoint.Query()
		query.Set("limit", "1000")
		endpoint.RawQuery = query.Encode()
	}
	for page := 0; page < 10; page++ {
		payload, err := fetchModelCatalog(ctx, client, endpoint, provider, apiKey, &remainingBytes)
		if err != nil {
			return nil, err
		}
		candidates, err := catalogCandidates(payload)
		if err != nil {
			return nil, err
		}
		for _, model := range candidates {
			if _, exists := seen[model.ID]; exists {
				continue
			}
			seen[model.ID] = struct{}{}
			models = append(models, model)
		}
		if provider != "anthropic" || !payload.HasMore {
			sort.SliceStable(models, func(i, j int) bool {
				return strings.ToLower(models[i].ID) < strings.ToLower(models[j].ID)
			})
			return models, nil
		}
		if _, repeated := cursors[payload.LastID]; payload.LastID == "" || repeated {
			return nil, errors.New("模型目录的分页游标无效，请手动输入模型 ID")
		}
		cursors[payload.LastID] = struct{}{}
		query := endpoint.Query()
		query.Set("after_id", payload.LastID)
		endpoint.RawQuery = query.Encode()
	}
	return nil, errors.New("模型目录分页过多，请手动输入模型 ID")
}

func fetchModelCatalog(
	ctx context.Context, client *http.Client, endpoint *url.URL,
	provider, apiKey string, remainingBytes *int,
) (modelCatalogPayload, error) {
	var payload modelCatalogPayload
	request, err := http.NewRequestWithContext(ctx, http.MethodGet, endpoint.String(), nil)
	if err != nil {
		return payload, errors.New("无法创建模型目录请求")
	}
	request.Header.Set("Accept", "application/json")
	if provider == "anthropic" {
		request.Header.Set("anthropic-version", "2023-06-01")
		if apiKey != "" {
			request.Header.Set("x-api-key", apiKey)
		}
	} else if apiKey != "" {
		request.Header.Set("Authorization", "Bearer "+apiKey)
	}
	response, err := client.Do(request)
	if err != nil {
		return payload, fmt.Errorf("无法连接模型目录: %w", err)
	}
	defer response.Body.Close()
	body, err := io.ReadAll(io.LimitReader(response.Body, int64(*remainingBytes)+1))
	if err != nil {
		return payload, errors.New("读取模型目录失败")
	}
	*remainingBytes -= len(body)
	if *remainingBytes < 0 {
		return payload, errors.New("模型目录响应过大")
	}
	if response.StatusCode < 200 || response.StatusCode >= 300 {
		switch response.StatusCode {
		case http.StatusUnauthorized, http.StatusForbidden:
			return payload, fmt.Errorf("模型服务拒绝访问（HTTP %d），请检查 API Key 和模型访问权限", response.StatusCode)
		case http.StatusNotFound, http.StatusMethodNotAllowed:
			return payload, fmt.Errorf("模型服务未开放该列表接口（HTTP %d），请检查 Base URL 或手动输入模型 ID", response.StatusCode)
		default:
			return payload, fmt.Errorf("模型目录返回 HTTP %d", response.StatusCode)
		}
	}
	if err := json.Unmarshal(body, &payload); err != nil {
		return payload, errors.New("模型目录没有返回可识别的 JSON，请检查 Base URL 或手动输入模型 ID")
	}
	return payload, nil
}

func catalogCandidates(payload modelCatalogPayload) ([]discoveredModel, error) {
	entries := payload.Data
	if entries == nil {
		// Alias keys, not nested canonical IDs, are the callable gateway routes.
		raw := strings.TrimSpace(string(payload.Models))
		switch {
		case strings.HasPrefix(raw, "["):
			if err := json.Unmarshal(payload.Models, &entries); err != nil {
				return nil, errors.New("模型列表格式不受支持，请手动输入模型 ID")
			}
		case strings.HasPrefix(raw, "{"):
			var aliases map[string]json.RawMessage
			if err := json.Unmarshal(payload.Models, &aliases); err != nil {
				return nil, errors.New("模型列表格式不受支持，请手动输入模型 ID")
			}
			for alias, value := range aliases {
				if !strings.HasPrefix(strings.TrimSpace(string(value)), "{") {
					continue
				}
				var item modelCatalogEntry
				if err := json.Unmarshal(value, &item); err != nil {
					continue
				}
				if strings.TrimSpace(alias) != "" {
					item.ID = alias
				}
				entries = append(entries, item)
			}
		default:
			return nil, errors.New("服务端没有返回受支持的模型列表，请检查 Base URL 或手动输入模型 ID")
		}
	}
	models := make([]discoveredModel, 0, len(entries))
	for _, item := range entries {
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
		id = strings.TrimSpace(id)
		if id == "" || len(id) > 200 {
			continue
		}
		name := item.DisplayName
		if name == "" {
			name = item.Name
		}
		if name == "" {
			name = id
		}
		contextWindow := item.ContextWindow
		if contextWindow == 0 {
			contextWindow = item.ContextLength
		}
		if contextWindow == 0 {
			contextWindow = item.ContextWindowCamel
		}
		detailParts := make([]string, 0, 3)
		for _, part := range []string{item.Details.Family, item.Details.ParameterSize, item.Details.QuantizationLevel} {
			if part != "" {
				detailParts = append(detailParts, part)
			}
		}
		models = append(models, discoveredModel{
			ID: id, Name: name, OwnedBy: item.OwnedBy, ContextWindow: contextWindow,
			Details: strings.Join(detailParts, " · "),
		})
	}
	return models, nil
}
