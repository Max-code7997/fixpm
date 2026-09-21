// Rule-table data model and lookup helpers.
//
// This mirrors src/fixpm/rules/base.py. The tables themselves are generated
// into rules_gen.go from the Python source, so this file only holds the type
// and the behaviour that both implementations must share.
package main

// ManagerSpec is the Go mirror of fixpm.rules.base.ManagerSpec.
type ManagerSpec struct {
	Name            string
	Binaries        []string
	Commands        []string
	Aliases         map[string]string
	Flags           map[string][]string
	GlobalFlags     []string
	ValueFlags      []string
	PackageCommands []string
	ArgRequired     []string
	TypoHints       map[string]string
	// Chains maps a chain command to its second-level verbs (`global` -> add,
	// remove, ... for yarn; `container` -> ls, prune, ... for docker). A
	// command absent from the map is treated as a plain subcommand.
	Chains       map[string][]string
	PackageFirst bool
	// SubcommandMinScore is the similarity floor for accepting a subcommand
	// typo. See fixpm.rules.base.ManagerSpec for why it differs per CLI.
	SubcommandMinScore float64
}

// Vocabulary mirrors ManagerSpec.vocabulary: commands() | aliases().
func (m *ManagerSpec) Vocabulary() []string {
	out := make([]string, 0, len(m.Commands)+len(m.Aliases))
	out = append(out, m.Commands...)
	for k := range m.Aliases {
		out = append(out, k)
	}
	return out
}

// Canonical mirrors ManagerSpec.canonical.
func (m *ManagerSpec) Canonical(token string) (string, bool) {
	for _, c := range m.Commands {
		if c == token {
			return c, true
		}
	}
	if v, ok := m.Aliases[token]; ok {
		return v, true
	}
	return "", false
}

// SpecForBinary mirrors fixpm.rules.base.spec_for_binary: the first registered
// spec whose binaries contain *binary*.
func SpecForBinary(binary string) *ManagerSpec {
	for i := range specs {
		for _, b := range specs[i].Binaries {
			if b == binary {
				return &specs[i]
			}
		}
	}
	return nil
}
