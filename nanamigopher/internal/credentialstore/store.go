// Package credentialstore provides a cross-platform interface for secure
// credential storage using OS keychains.
package credentialstore

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

// ValidateAndSave validates and stores an API key.
func (m *Manager) ValidateAndSave(engine, apiKey string) error {
	if err := m.validateAPIKey(engine, apiKey); err != nil {
		return err
	}
	return m.store.Save("search", engine, apiKey)
}

func (m *Manager) validateAPIKey(engine, apiKey string) error {
	// TODO: implement engine-specific validation
	switch engine {
	case "tavily", "google", "duckduckgo":
		return nil
	default:
		return nil
	}
}
