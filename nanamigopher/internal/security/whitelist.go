// Package security provides whitelisting for security filter bypass.
package security

import (
	"regexp"
	"strings"
)

// Whitelist allows safe inputs to bypass blocking rules.
type Whitelist struct {
	GlobalKeywords []string
	UserKeywords   []string
	UserRegex      []*regexp.Regexp
}

// IsWhitelisted checks if the input matches any whitelisted pattern.
func (w *Whitelist) IsWhitelisted(input string) bool {
	lower := strings.ToLower(input)
	allKeywords := append(w.GlobalKeywords, w.UserKeywords...)
	for _, keyword := range allKeywords {
		if strings.Contains(lower, strings.ToLower(keyword)) {
			return true
		}
	}
	for _, regex := range w.UserRegex {
		if regex.MatchString(input) {
			return true
		}
	}
	return false
}
