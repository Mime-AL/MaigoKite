//go:build darwin

// Package credentialstore provides macOS keychain-backed credential storage.
package credentialstore

// darwinKeychain implements CredentialStore using macOS Keychain Access.
type darwinKeychain struct{}

// Save stores a credential in the macOS Keychain.
func (k *darwinKeychain) Save(service, username, secret string) error {
	// TODO: use keychain item APIs
	_ = service
	_ = username
	_ = secret
	return nil
}

// Get retrieves a credential from the macOS Keychain.
func (k *darwinKeychain) Get(service, username string) (string, error) {
	// TODO: query keychain for the item
	_ = service
	_ = username
	return "", nil
}

// Delete removes a credential from the macOS Keychain.
func (k *darwinKeychain) Delete(service, username string) error {
	// TODO: delete keychain item
	_ = service
	_ = username
	return nil
}

// List returns all usernames for a service in the Keychain.
func (k *darwinKeychain) List(service string) ([]string, error) {
	// TODO: search keychain for matching items
	_ = service
	return nil, nil
}
