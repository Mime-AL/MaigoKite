// Package credentialstore provides a cross-platform interface for secure
// credential storage using OS keychains.
package credentialstore

import (
	"errors"
	"fmt"
	"strings"

	keyring "github.com/zalando/go-keyring"
)

var ErrListUnsupported = errors.New("the OS keyring does not support enumerating credentials")

type osKeyring struct{}

// NewOSStore returns a store backed by Keychain, Secret Service, or Windows Credential Manager.
func NewOSStore() CredentialStore { return &osKeyring{} }

func (s *osKeyring) Save(service, username, secret string) error {
	if strings.TrimSpace(service) == "" || strings.TrimSpace(username) == "" || secret == "" {
		return errors.New("service, username, and secret are required")
	}
	return keyring.Set("NanamiGopher/"+service, username, secret)
}
func (s *osKeyring) Get(service, username string) (string, error) {
	return keyring.Get("NanamiGopher/"+service, username)
}
func (s *osKeyring) Delete(service, username string) error {
	return keyring.Delete("NanamiGopher/"+service, username)
}
func (s *osKeyring) List(string) ([]string, error) { return nil, ErrListUnsupported }

// CredentialStore is the interface for storing and retrieving secrets.
// Platform-specific implementations use the native keychain API.
type CredentialStore interface {
	// Save stores a credential by service and username.
	Save(service, username, secret string) error

	// Get retrieves a stored credential.
	Get(service, username string) (string, error)

	// Delete removes a credential.
	Delete(service, username string) error

	// List returns all usernames for a given service.
	List(service string) ([]string, error)
}

// Manager provides a high-level API for credential operations.
type Manager struct {
	store CredentialStore
}

// NewManager creates a credential manager with the given store.
func NewManager(store CredentialStore) *Manager {
	return &Manager{store: store}
}

// SaveSearchKey stores an API key for a search engine.
func (m *Manager) SaveSearchKey(engine, apiKey string) error {
	return m.store.Save("search", engine, apiKey)
}

// GetSearchKey retrieves a search engine API key.
func (m *Manager) GetSearchKey(engine string) (string, error) {
	return m.store.Get("search", engine)
}

func (m *Manager) GetSearchKeyForWorkspace(workspace, engine string) (string, error) {
	return m.store.Get("search/"+workspace, engine)
}

// GetModelKeyForWorkspace retrieves the primary chat model credential.
func (m *Manager) GetModelKeyForWorkspace(workspace, provider string) (string, error) {
	return m.GetForWorkspace(workspace, "model."+provider)
}

// GetModelProfileKeyForWorkspace retrieves a credential isolated to one model profile.
func (m *Manager) GetModelProfileKeyForWorkspace(workspace, modelID string) (string, error) {
	return m.GetForWorkspace(workspace, "model-profile."+modelID)
}

// GetForWorkspace retrieves a supported credential by its public reference name.
func (m *Manager) GetForWorkspace(workspace, service string) (string, error) {
	scope, username, err := credentialLocation(workspace, service)
	if err != nil {
		return "", err
	}
	return m.store.Get(scope, username)
}

// DeleteForWorkspace removes a supported credential without exposing it.
func (m *Manager) DeleteForWorkspace(workspace, service string) error {
	scope, username, err := credentialLocation(workspace, service)
	if err != nil {
		return err
	}
	return m.store.Delete(scope, username)
}

// Delete removes a credential without exposing its value.
func (m *Manager) Delete(service, username string) error {
	return m.store.Delete(service, username)
}

// ValidateAndSave validates and stores an API key.
func (m *Manager) ValidateAndSave(engine, apiKey string) error {
	return m.ValidateAndSaveForWorkspace("personal", engine, apiKey)
}

func (m *Manager) ValidateAndSaveForWorkspace(workspace, engine, apiKey string) error {
	if err := m.validateAPIKey(engine, apiKey); err != nil {
		return err
	}
	scope, username, err := credentialLocation(workspace, engine)
	if err != nil {
		return err
	}
	return m.store.Save(scope, username, apiKey)
}

func (m *Manager) validateAPIKey(engine, apiKey string) error {
	trimmed := strings.TrimSpace(apiKey)
	if trimmed == "" {
		return errors.New("API key is required")
	}
	if !strings.HasPrefix(engine, "model.") && len(trimmed) < 8 {
		return errors.New("API key is too short")
	}
	if strings.HasPrefix(engine, "model-profile.") {
		_, _, err := credentialLocation("validation", engine)
		return err
	}
	switch engine {
	case "tavily", "google", "model.openai", "model.anthropic", "model.openai_compatible":
		return nil
	default:
		return fmt.Errorf("unsupported credential service %q", engine)
	}
}

func credentialLocation(workspace, service string) (string, string, error) {
	if strings.TrimSpace(workspace) == "" {
		return "", "", errors.New("workspace is required")
	}
	switch service {
	case "tavily", "google":
		return "search/" + workspace, service, nil
	case "model.openai", "model.anthropic", "model.openai_compatible":
		return "model/" + workspace, strings.TrimPrefix(service, "model."), nil
	default:
		if strings.HasPrefix(service, "model-profile.") {
			modelID := strings.TrimPrefix(service, "model-profile.")
			if !strings.HasPrefix(modelID, "model_") || len(modelID) > 86 {
				return "", "", fmt.Errorf("invalid model profile credential %q", service)
			}
			for _, char := range modelID {
				if (char < 'a' || char > 'z') && (char < 'A' || char > 'Z') &&
					(char < '0' || char > '9') && char != '_' && char != '-' {
					return "", "", fmt.Errorf("invalid model profile credential %q", service)
				}
			}
			return "model-profile/" + workspace, modelID, nil
		}
		return "", "", fmt.Errorf("unsupported credential service %q", service)
	}
}
