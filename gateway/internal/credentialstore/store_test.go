package credentialstore

import "testing"

type fakeStore struct {
	service  string
	username string
	value    string
}

func (s *fakeStore) Save(service, username, secret string) error {
	s.service, s.username, s.value = service, username, secret
	return nil
}
func (s *fakeStore) Get(service, username string) (string, error) {
	s.service, s.username = service, username
	return s.value, nil
}
func (s *fakeStore) Delete(service, username string) error {
	s.service, s.username, s.value = service, username, ""
	return nil
}
func (s *fakeStore) List(string) ([]string, error) { return nil, nil }

func TestValidateAndSave(t *testing.T) {
	store := &fakeStore{}
	manager := NewManager(store)
	if err := manager.ValidateAndSave("tavily", "short"); err == nil {
		t.Fatal("expected short key to be rejected")
	}
	if err := manager.ValidateAndSave("tavily", "valid-key-value"); err != nil {
		t.Fatal(err)
	}
	if store.value != "valid-key-value" {
		t.Fatal("credential was not delegated to store")
	}
}

func TestGoogleCredentialRequiresKeyAndCX(t *testing.T) {
	store := &fakeStore{}
	manager := NewManager(store)
	if err := manager.ValidateAndSaveForWorkspace("personal", "google", "google-api-key"); err == nil {
		t.Fatal("expected Google credential without CX to be rejected")
	}
	if err := manager.ValidateAndSaveForWorkspace("personal", "google", "google-api-key:search-engine-id"); err != nil {
		t.Fatal(err)
	}
	if store.value != "google-api-key:search-engine-id" {
		t.Fatal("Google credential was not delegated to store")
	}
}

func TestModelCredentialsAreProviderScoped(t *testing.T) {
	store := &fakeStore{}
	manager := NewManager(store)
	if err := manager.ValidateAndSaveForWorkspace("personal", "model.openai", "sk-test"); err != nil {
		t.Fatal(err)
	}
	if store.service != "model/personal" || store.username != "openai" {
		t.Fatalf("unexpected keyring location %q/%q", store.service, store.username)
	}
	if _, err := manager.GetModelKeyForWorkspace("personal", "anthropic"); err != nil {
		t.Fatal(err)
	}
	if store.username != "anthropic" {
		t.Fatal("provider credentials must not share a username")
	}
}
