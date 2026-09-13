//go:build linux

// Package credentialstore provides Linux libsecret-backed credential storage.
package credentialstore

// linuxLibSecret implements CredentialStore using the Linux Secret Service API.
type linuxLibSecret struct{}

// Save stores a credential in the Linux keyring via libsecret.
func (k *linuxLibSecret) Save(service, username, secret string) error {
	// TODO: use libsecret D-Bus API
	_ = service
	_ = username
	_ = secret
	return nil
}

// Get retrieves a credential from the Linux keyring.
func (k *linuxLibSecret) Get(service, username string) (string, error) {
	// TODO: query SecretService for the item
	_ = service
	_ = username
	return "", nil
}

// Delete removes a credential.
func (k *linuxLibSecret) Delete(service, username string) error {
	// TODO: delete keyring item
	_ = service
	_ = username
	return nil
}

// List returns all usernames for a service.
func (k *linuxLibSecret) List(service string) ([]string, error) {
	// TODO: enumerate keyring items
	_ = service
	return nil, nil
}
