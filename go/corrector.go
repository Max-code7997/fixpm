// Turn analyzer issues into concrete, ranked replacement commands — port of
// src/fixpm/corrector.py.
package main

import (
	"sort"
	"strings"
	"time"
)

// placeholders mirrors corrector._PLACEHOLDERS: the visible placeholder shown
// when a fix needs manual input (such fixes are never auto-executed).
var placeholders = map[string]string{
	"run":       "<script>",
	"exec":      "<package> [args...]",
	"dlx":       "<package> [args...]",
	"add":       "<package>",
	"install":   "<package>",
	"remove":    "<package>",
	"uninstall": "<package>",
	"why":       "<package>",
	"info":      "<package>",
	"create":    "<initializer>",
	"config":    "<key> <value>",
	"cache":     "<action>",
	"pkg":       "<action>",
}

// Matches the Python default timeout of 2.5s per request.
var defaultRegistry = NewNpmRegistry(2500 * time.Millisecond)

// ratioScore mirrors corrector._ratio_score.
func ratioScore(ratio float64) float64 {
	return PyRound(0.5+0.45*ratio, 3)
}

// replaceToken mirrors corrector._replace: patch one token and re-join.
func replaceToken(tokens []string, index int, newToken string) string {
	if index < 0 || index >= len(tokens) {
		return ShlexJoin(tokens)
	}
	patched := make([]string, len(tokens))
	copy(patched, tokens)
	patched[index] = newToken
	return ShlexJoin(patched)
}

// GetCorrections mirrors corrector.get_corrections: at most 3 fixes, best first.
//
// A nil registry falls back to the package-level default, matching the Python
// `client = client or _default_client()`.
func GetCorrections(text string, spec *ManagerSpec, client *NpmRegistry) []Correction {
	tokens, found, issues := Analyze(text, spec)
	if found == nil || len(issues) == 0 {
		return nil
	}
	if client == nil {
		client = defaultRegistry
	}

	all := []Correction{}
	for _, issue := range issues {
		all = append(all, fixIssue(tokens, found, issue, client)...)
	}

	// Dedupe by command keeping the highest score. Python relies on dict
	// insertion order, so the first command seen keeps its rank position.
	best := map[string]Correction{}
	order := []string{}
	for _, c := range all {
		prev, seen := best[c.Command]
		if !seen {
			best[c.Command] = c
			order = append(order, c.Command)
			continue
		}
		if c.Score > prev.Score {
			best[c.Command] = c
		}
	}

	ranked := make([]Correction, 0, len(order))
	for _, cmd := range order {
		ranked = append(ranked, best[cmd])
	}
	sort.SliceStable(ranked, func(i, j int) bool {
		if ranked[i].Score != ranked[j].Score {
			return ranked[i].Score > ranked[j].Score
		}
		return ranked[i].Command < ranked[j].Command
	})
	if len(ranked) > 3 {
		ranked = ranked[:3]
	}
	return ranked
}

// fixIssue mirrors corrector._fix_issue.
func fixIssue(tokens []string, spec *ManagerSpec, issue Issue,
	client *NpmRegistry) []Correction {

	switch issue.Kind {
	case KindSubcommandTypo:
		out := []Correction{}
		hinted, hasHint := spec.TypoHints[strings.ToLower(issue.Token)]
		for _, cand := range head(issue.Candidates, 3) {
			score := ratioScore(Similarity(strings.ToLower(issue.Token), cand))
			if hasHint && cand == hinted {
				score = 0.95
			}
			out = append(out, Correction{
				Command:    replaceToken(tokens, issue.Index, cand),
				Kind:       issue.Kind,
				Score:      score,
				Message:    issue.Message,
				Executable: true,
			})
		}
		return out

	case KindFlagTypo:
		out := []Correction{}
		for _, cand := range head(issue.Candidates, 2) {
			out = append(out, Correction{
				Command:    replaceToken(tokens, issue.Index, cand),
				Kind:       issue.Kind,
				Score:      ratioScore(Similarity(issue.Token, cand)),
				Message:    issue.Message,
				Executable: true,
			})
		}
		return out

	case KindMissingDashes:
		if len(issue.Candidates) == 0 {
			return nil
		}
		return []Correction{{
			Command:    replaceToken(tokens, issue.Index, issue.Candidates[0]),
			Kind:       issue.Kind,
			Score:      0.9,
			Message:    issue.Message,
			Executable: true,
		}}

	case KindArgRequired:
		placeholder, ok := placeholders[issue.Token]
		if !ok {
			placeholder = "<arguments>"
		}
		return []Correction{{
			Command:    ShlexJoin(tokens) + " " + placeholder,
			Kind:       issue.Kind,
			Score:      0.6,
			Message:    issue.Message,
			Executable: false, // needs manual input: never auto-executed
		}}

	case KindPackageTypo:
		name := baseName(issue.Token)
		out := []Correction{}
		for _, s := range client.Suggest(name, 3) {
			if strings.EqualFold(s.Name, name) {
				continue
			}
			newToken := strings.Replace(issue.Token, name, s.Name, 1)
			out = append(out, Correction{
				Command: replaceToken(tokens, issue.Index, newToken),
				Kind:    issue.Kind,
				Score:   s.Score,
				Message: "package '" + name + "' -> '" + s.Name + "' (" +
					formatDownloads(s.WeeklyDownloads) + "/week)",
				Executable: true,
			})
		}
		return out
	}
	return nil
}

// head mirrors Python's `seq[:n]` for a slice.
func head(items []string, n int) []string {
	if len(items) > n {
		return items[:n]
	}
	return items
}
