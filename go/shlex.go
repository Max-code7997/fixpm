// Shell-word splitting and joining — port of the bits of Python's shlex that
// fixpm actually relies on.
//
// Why not just strings.Fields? Because the hook feeds fixpm the raw command
// line, which routinely contains quotes and escapes:
//
//	npm install "lodash@^4" --prefix './my dir'
//
// Splitting that on whitespace alone would produce different tokens than the
// Python implementation, so the two binaries would disagree about the same
// command. Parity here is a correctness requirement, not a nicety.
package main

import (
	"errors"
	"strings"
)

func isSpace(r rune) bool {
	switch r {
	case ' ', '\t', '\n', '\r', '\v', '\f':
		return true
	}
	return false
}

// ShlexSplit mirrors shlex.split(text, comments=False, posix=True):
// whitespace-delimited, honours single/double quotes and backslash escapes,
// and treats '#' as an ordinary character.
func ShlexSplit(text string) ([]string, error) {
	rs := []rune(text)

	tokens := []string{}
	cur := make([]rune, 0, 16)
	started := false

	flush := func() {
		if started {
			tokens = append(tokens, string(cur))
			cur = cur[:0]
			started = false
		}
	}

	for i := 0; i < len(rs); {
		c := rs[i]
		switch {
		case isSpace(c):
			flush()
			i++

		case c == '\'':
			// Single quotes: everything literal until the closing quote
			// (Python's shlex does not process escapes inside '').
			started = true
			i++
			for i < len(rs) && rs[i] != '\'' {
				cur = append(cur, rs[i])
				i++
			}
			if i >= len(rs) {
				return nil, errors.New("No closing quotation")
			}
			i++

		case c == '"':
			// Double quotes: backslash escapes only for the characters
			// Python's shlex considers escapable inside "" .
			started = true
			i++
			for i < len(rs) && rs[i] != '"' {
				if rs[i] == '\\' && i+1 < len(rs) {
					switch rs[i+1] {
					case '"', '\\', '$', '`':
						cur = append(cur, rs[i+1])
						i += 2
						continue
					}
				}
				cur = append(cur, rs[i])
				i++
			}
			if i >= len(rs) {
				return nil, errors.New("No closing quotation")
			}
			i++

		case c == '\\':
			started = true
			if i+1 >= len(rs) {
				return nil, errors.New("No escaped character")
			}
			cur = append(cur, rs[i+1])
			i += 2

		default:
			started = true
			cur = append(cur, c)
			i++
		}
	}
	flush()
	return tokens, nil
}

// Tokenize mirrors detector.tokenize: shlex first, plain whitespace split as a
// fallback when the line has unbalanced quotes.
func Tokenize(text string) []string {
	if tokens, err := ShlexSplit(text); err == nil {
		return tokens
	}
	return strings.Fields(text)
}

// ShlexQuote mirrors shlex.quote (Python 3.3+).
func ShlexQuote(s string) string {
	if s == "" {
		return "''"
	}
	for _, r := range s {
		if !isShlexSafe(r) {
			return "'" + strings.ReplaceAll(s, "'", `'\''`) + "'"
		}
	}
	return s
}

// isShlexSafe reports whether r may appear unquoted. Mirrors the ASCII-only
// character class in CPython's shlex._find_unsafe: [^\w@%+=:,./-] with
// re.ASCII, i.e. \w == [A-Za-z0-9_].
func isShlexSafe(r rune) bool {
	switch {
	case r >= 'a' && r <= 'z', r >= 'A' && r <= 'Z', r >= '0' && r <= '9':
		return true
	}
	switch r {
	case '_', '@', '%', '+', '=', ':', ',', '.', '/', '-':
		return true
	}
	return false
}

// ShlexJoin mirrors shlex.join: quote each token, then space-join.
func ShlexJoin(tokens []string) string {
	parts := make([]string, len(tokens))
	for i, t := range tokens {
		parts[i] = ShlexQuote(t)
	}
	return strings.Join(parts, " ")
}
