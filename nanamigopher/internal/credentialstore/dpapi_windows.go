//go:build windows

// Package credentialstore provides Windows DPAPI-backed credential storage.
package credentialstore

// windowsDPAPI implements CredentialStore using Windows Data Protection API.
type windowsDPAPI struct{}

// Save stores a credential using Windows DPAPI.
func (k *windowsDPAPI) Save(service, username, secret string) error {
	// TODO: use CryptProtectData
	_ = service
	_ = username
	_ = secret
	return nil
}

// Get retrieves a credential using Windows DPAPI.
func (k *windowsDPAPI) Get(service, username string) (string, error) {
	// TODO: use CryptUnprotectData
	_ = service
	_ = username
	return "", nil
}

// Delete removes a credential.
func (k *windowsDPAPI) Delete(service, username string) error {
	// TODO: delete stored credential
	_ = service
	_ = username
	return nil
}

// List returns all usernames for a service.
func (k *windowsDPAPI) List(service string) ([]string, error) {
	// TODO: enumerate stored credentials
	_ = service
	return nil, nil
}
