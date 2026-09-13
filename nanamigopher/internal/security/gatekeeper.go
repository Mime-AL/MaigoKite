// Package security provides input sanitization and length truncation.
package security

// Gatekeeper enforces input length limits by truncating oversized inputs.
type Gatekeeper struct {
	maxTokens int
}

// NewGatekeeper creates a Gatekeeper with the given token limit.
func NewGatekeeper(maxTokens int) *Gatekeeper {
	return &Gatekeeper{maxTokens: maxTokens}
}

// Filter truncates input that exceeds the token limit.
// Returns the filtered string and whether truncation occurred.
func (g *Gatekeeper) Filter(input string) (string, bool) {
	// Rough token estimation: ~4 characters per token
	estimatedTokens := len(input) / 4
	if estimatedTokens <= g.maxTokens {
		return input, false
	}
	truncated := input[:g.maxTokens*4]
	return truncated, true
}
