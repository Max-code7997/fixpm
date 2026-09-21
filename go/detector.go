// Classification engine — port of src/fixpm/detector.py.
//
// One generic engine consumes every ManagerSpec; per-manager knowledge lives
// entirely in the generated rule tables. Kept line-for-line comparable with the
// Python source so a reviewer can diff the two side by side.
package main

import (
	"regexp"
	"sort"
	"strings"
)

// ---------------------------------------------------------------- model

// IssueKind mirrors fixpm.rules.base.IssueKind.
type IssueKind string

const (
	KindSubcommandTypo IssueKind = "subcommand-typo"
	KindFlagTypo       IssueKind = "flag-typo"
	KindMissingDashes  IssueKind = "missing-dashes"
	KindArgRequired    IssueKind = "argument-required"
	KindPackageTypo    IssueKind = "package-typo"
)

// KindLabel mirrors fixpm.rules.base.KIND_LABEL.
var KindLabel = map[IssueKind]string{
	KindSubcommandTypo: "command fix",
	KindFlagTypo:       "flag fix",
	KindMissingDashes:  "missing --",
	KindArgRequired:    "missing argument",
	KindPackageTypo:    "package fix",
}

// Issue mirrors fixpm.rules.base.Issue.
type Issue struct {
	Kind       IssueKind
	Token      string
	Index      int
	Message    string
	Candidates []string
}

// Correction mirrors fixpm.rules.base.Correction.
type Correction struct {
	Command    string
	Kind       IssueKind
	Score      float64
	Message    string
	Executable bool
}

// ---------------------------------------------------------------- detector

var pkgRe = regexp.MustCompile(
	`(?i)^(@[a-z0-9-~][a-z0-9-._~]*/)?[a-z0-9-~][a-z0-9-._~]*$`)

// LooksLikePackage mirrors detector.looks_like_package: a conservative
// npm-package-name shape check that rules out paths, globs and files.
func LooksLikePackage(token string) bool {
	if token == "" || strings.ContainsAny(token, "*~=\\\"") {
		return false
	}
	if strings.HasPrefix(token, ".") || strings.HasPrefix(token, "~") {
		return false
	}
	if strings.Contains(token, "/") && !strings.HasPrefix(token, "@") {
		return false
	}
	return pkgRe.MatchString(token)
}

// nearest mirrors detector._nearest. The pool is lowercased and sorted before
// ranking, exactly as the Python version does.
func nearest(token string, pool []string, top int, minScore float64) []string {
	lowered := make([]string, 0, len(pool))
	for _, p := range pool {
		lowered = append(lowered, strings.ToLower(p))
	}
	sort.Strings(lowered)
	return Rank(strings.ToLower(token), lowered, top, minScore)
}

// hinted mirrors detector._hinted: the curated hint for *token* if it is valid
// in this slot. One TypoHints map feeds both the command slot and the
// chain-verb slot, so the target is checked against the slot's own vocabulary.
func hinted(token string, spec *ManagerSpec, pool []string) []string {
	hint, ok := spec.TypoHints[strings.ToLower(token)]
	if !ok || !contains(pool, hint) {
		return nil
	}
	return []string{hint}
}

// subCandidates mirrors detector._sub_candidates.
func subCandidates(token string, spec *ManagerSpec) []string {
	if hint := hinted(token, spec, spec.Vocabulary()); hint != nil {
		return hint
	}
	return nearest(token, spec.Vocabulary(), 3, spec.SubcommandMinScore)
}

// Analyze mirrors detector.analyze.
func Analyze(text string, spec *ManagerSpec) ([]string, *ManagerSpec, []Issue) {
	tokens := Tokenize(text)
	index, located := locate(tokens, spec)
	if located == nil {
		return tokens, nil, nil
	}
	if index < 0 {
		// Forced table whose binary is absent: synthesise it so the fix is a
		// runnable command. See detector.analyze for the rationale.
		tokens = append([]string{located.Binaries[0]}, tokens...)
		index = 0
	}
	if located.PackageFirst {
		return tokens, located, analyzePackageFirst(located, tokens, index+1)
	}
	return tokens, located, analyzeSubcommand(located, tokens, index+1)
}

// locate mirrors detector._locate.
func locate(tokens []string, spec *ManagerSpec) (int, *ManagerSpec) {
	limit := len(tokens)
	if limit > 4 {
		limit = 4
	}
	if spec != nil {
		for i := 0; i < limit; i++ {
			for _, b := range spec.Binaries {
				if tokens[i] == b {
					return i, spec
				}
			}
		}
		// Binary absent: -1 tells Analyze to synthesise it. See
		// detector._locate for why returning nil here was wrong.
		return -1, spec
	}
	for i := 0; i < limit; i++ {
		if found := SpecForBinary(tokens[i]); found != nil {
			return i, found
		}
	}
	return -1, nil
}

// contains reports membership for the small string slices used by the rules.
func contains(list []string, want string) bool {
	for _, v := range list {
		if v == want {
			return true
		}
	}
	return false
}

// scanLeadingFlags mirrors the global-flag prelude shared by both analyzers.
func scanLeadingFlags(spec *ManagerSpec, rest []string, start int) ([]Issue, int) {
	issues := []Issue{}
	i := 0
	for i < len(rest) && strings.HasPrefix(rest[i], "-") {
		flag := rest[i]
		if contains(spec.ValueFlags, flag) && i+1 < len(rest) {
			i += 2
			continue
		}
		if !contains(spec.GlobalFlags, flag) {
			if near := nearest(flag, spec.GlobalFlags, 2, 0.6); len(near) > 0 {
				issues = append(issues, Issue{
					Kind:       KindFlagTypo,
					Token:      flag,
					Index:      start + i,
					Message:    "Unknown global flag '" + flag + "' — did you mean " + near[0] + "?",
					Candidates: near,
				})
			}
		}
		i++
	}
	return issues, i
}

// analyzeSubcommand mirrors detector._analyze_subcommand.
func analyzeSubcommand(spec *ManagerSpec, tokens []string, start int) []Issue {
	rest := tokens[start:]
	issues, i := scanLeadingFlags(spec, rest, start)

	if i >= len(rest) {
		return issues
	}

	sub := rest[i]
	subAbs := start + i
	canon, ok := spec.Canonical(sub)

	if !ok {
		if candidates := subCandidates(sub, spec); len(candidates) > 0 {
			issues = append(issues, Issue{
				Kind:       KindSubcommandTypo,
				Token:      sub,
				Index:      subAbs,
				Message:    "'" + sub + "' is not a " + spec.Name + " command",
				Candidates: candidates,
			})
		}
		// One fix at a time: stop validating after an unknown command.
		return issues
	}

	// Chain commands like `yarn global add <pkg>`, `docker container ls` or
	// `go mod tidy` — absorb the second-level verb. Which commands chain is a
	// per-CLI fact (spec.Chains); the slot gets typo tolerance too, so
	// `yarn global ad x` still resolves the chain and reports the typo.
	extra := 0
	verbs := spec.Chains[canon]
	if len(verbs) > 0 && i+1 < len(rest) {
		nxt := rest[i+1]
		if contains(verbs, nxt) {
			extra = 1
			canon = canon + " " + nxt
		} else {
			// Curated hints first (short transpositions such as `ud` -> `up`
			// fall under every floor), validated against this slot.
			near := hinted(nxt, spec, verbs)
			if near == nil {
				near = nearest(nxt, verbs, 1, spec.SubcommandMinScore)
			}
			if len(near) > 0 {
				issues = append(issues, Issue{
					Kind:       KindSubcommandTypo,
					Token:      nxt,
					Index:      start + i + 1,
					Message:    "'" + nxt + "' is not a " + spec.Name + " subcommand of '" + canon + "'",
					Candidates: near,
				})
				extra = 1
				canon = canon + " " + near[0]
			}
		}
	}

	effective := canon
	if idx := strings.LastIndex(canon, " "); idx >= 0 {
		effective = canon[idx+1:]
	}
	allowed := spec.Flags[effective]

	type positional struct {
		index int
		token string
	}
	positionals := []positional{}

	j := i + 1 + extra
	for j < len(rest) {
		token := rest[j]
		if token == "--" { // passthrough separator: everything after is exempt
			break
		}
		if strings.HasPrefix(token, "-") {
			if len(allowed) > 0 && !contains(allowed, token) &&
				!contains(spec.GlobalFlags, token) {
				if near := nearest(token, allowed, 2, 0.6); len(near) > 0 {
					issues = append(issues, Issue{
						Kind:  KindFlagTypo,
						Token: token,
						Index: start + j,
						Message: "Unknown flag '" + token + "' for `" + spec.Name +
							" " + effective + "` — did you mean " + near[0] + "?",
						Candidates: near,
					})
				}
			}
			if contains(spec.ValueFlags, token) {
				j++ // skip the consumed value
			}
		} else {
			positionals = append(positionals, positional{j, token})
		}
		j++
	}

	// `npm install express save-dev` -> missing dashes on `save-dev`
	dashless := make(map[string]string, len(allowed))
	for _, f := range allowed {
		dashless[strings.TrimLeft(f, "-")] = f
	}
	flagged := make(map[int]bool, len(positionals))
	for _, p := range positionals {
		if runeLen(p.token) > 1 {
			if want, hit := dashless[p.token]; hit {
				issues = append(issues, Issue{
					Kind:       KindMissingDashes,
					Token:      p.token,
					Index:      start + p.index,
					Message:    "Missing flag prefix — did you mean " + want + "?",
					Candidates: []string{want},
				})
				flagged[p.index] = true
			}
		}
	}
	kept := positionals[:0:0]
	for _, p := range positionals {
		if !flagged[p.index] {
			kept = append(kept, p)
		}
	}
	positionals = kept

	// Only report a missing argument when nothing else was flagged. For
	// `npm uninstall save-dev` the real problem is the missing dashes, and
	// pairing it with "needs an argument" emitted a second suggestion that
	// still contained the very typo the first one fixes.
	if contains(spec.ArgRequired, canon) && len(positionals) == 0 &&
		len(flagged) == 0 && extra == 0 {
		issues = append(issues, Issue{
			Kind:  KindArgRequired,
			Token: sub,
			Index: subAbs,
			Message: "`" + spec.Name + " " + sub + "` needs an argument (see `" +
				spec.Name + " help " + effective + "`)",
		})
	}

	// Chained package commands are listed explicitly ("global add"), so this
	// stays a plain membership test. See detector._analyze_subcommand.
	if contains(spec.PackageCommands, canon) {
		checked := 0
		for _, p := range positionals {
			if checked >= 2 {
				break
			}
			if contains(spec.Vocabulary(), strings.ToLower(p.token)) ||
				!LooksLikePackage(p.token) {
				continue
			}
			issues = append(issues, Issue{
				Kind:    KindPackageTypo,
				Token:   p.token,
				Index:   start + p.index,
				Message: "Check package name '" + p.token + "'",
			})
			checked++
		}
	}
	return issues
}

// analyzePackageFirst mirrors detector._analyze_package_first.
func analyzePackageFirst(spec *ManagerSpec, tokens []string, start int) []Issue {
	rest := tokens[start:]
	issues, i := scanLeadingFlags(spec, rest, start)

	if i >= len(rest) {
		issues = append(issues, Issue{
			Kind:  KindArgRequired,
			Token: spec.Name,
			Index: start - 1,
			Message: "`" + spec.Name +
				"` needs a package or binary to run",
		})
		return issues
	}

	pkg := rest[i]
	if LooksLikePackage(pkg) {
		issues = append(issues, Issue{
			Kind:    KindPackageTypo,
			Token:   pkg,
			Index:   start + i,
			Message: "Check package name '" + pkg + "'",
		})
	}
	return issues
}
