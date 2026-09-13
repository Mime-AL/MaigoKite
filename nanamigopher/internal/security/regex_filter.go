// Package security provides regex-based prompt injection detection.
package security

import "regexp"

// Pattern represents a regex pattern for detecting malicious input.
type Pattern struct {
	Name     string
	Regex    *regexp.Regexp
	Severity string // "block" or "warn"
}

// RegexFilter detects prompt injection attempts using regex patterns.
type RegexFilter struct {
	patterns []Pattern
}

// NewRegexFilter creates a filter with built-in injection detection patterns.
func NewRegexFilter() *RegexFilter {
	return &RegexFilter{
		patterns: []Pattern{
			{
				Name:     "ignore_instructions",
				Regex:    regexp.MustCompile(`(?i)(ignore\s+(all\s+)?(previous\s+)?(system\s+)?instructions?)`),
				Severity: "block",
			},
			{
				Name:     "system_prompt_leak",
				Regex:    regexp.MustCompile(`(?i)(tell\s+me\s+your\s+(system\s+)?prompt|reveal\s+your\s+instructions)`),
				Severity: "block",
			},
			{
				Name:     "role_escape",
				Regex:    regexp.MustCompile(`(?i)(daniel|do\s+anything|DAN\s+mode|jailbreak)`),
				Severity: "block",
			},
		},
	}
}

// Match represents a regex pattern match result.
type Match struct {
	PatternName string
	Severity    string
}

// Check runs all patterns against the input and returns matches.
func (f *RegexFilter) Check(input string) []Match {
	var matches []Match
	for _, pattern := range f.patterns {
		if pattern.Regex.MatchString(input) {
			matches = append(matches, Match{
				PatternName: pattern.Name,
				Severity:    pattern.Severity,
			})
		}
	}
	return matches
}
