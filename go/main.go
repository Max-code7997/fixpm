// fixpm-probe — the fast path the shell hook runs after every failed
// npm-family command.
//
// The Python CLI pays ~165 ms just to start an interpreter, and the hook runs
// on the prompt path, so the probe binary exists to make this specific call
// (detect typos, print fixes, exit 0/1) essentially free.
//
// It is NOT a replacement for `fixpm`: interactive selection and --init stay
// in Python. The probe deliberately requires --dry-run so it can never be
// mistaken for the full CLI.
package main

import (
	"fmt"
	"io"
	"os"
	"strings"
	"time"
)

const usage = `fixpm-probe — fast typo probe for the fixpm shell hook

Usage:
  fixpm-probe --dry-run "<failed command>"     print fixes, exit 0 if any
  fixpm-probe --version

Options:
  -m, --manager NAME   force a package manager instead of auto-detecting
      --deadline DUR   total budget for npm registry lookups (e.g. 400ms)
      --offline        never touch the npm registry (curated map + corpus only)
  -V, --version        show version and exit

Without --deadline the probe matches the Python CLI: one 2.5s timeout per
registry request. The shell hook passes a budget so a slow network can never
hold the prompt hostage.

Exit codes: 0 = at least one fix found, 1 = no fix, 2 = usage error.
This binary only implements the probe path; use the fixpm CLI for the rest.
`

func main() {
	os.Exit(run(os.Args[1:], os.Stdout, os.Stderr))
}

// run takes explicit writers so tests can capture output instead of touching
// the real process streams.
func run(args []string, stdout, stderr io.Writer) int {
	var (
		dryRun      bool
		offline     bool
		showVersion bool
		manager     string
		deadline    time.Duration
		words       []string
	)

	for i := 0; i < len(args); i++ {
		switch a := args[i]; {
		case a == "--dry-run":
			dryRun = true
		case a == "--offline":
			offline = true
		case a == "-V" || a == "--version":
			showVersion = true
		case a == "-m" || a == "--manager":
			if i+1 < len(args) {
				i++
				manager = args[i]
			}
		case strings.HasPrefix(a, "--manager="):
			manager = strings.TrimPrefix(a, "--manager=")
		case a == "--deadline":
			if i+1 < len(args) {
				i++
				d, err := time.ParseDuration(args[i])
				if err != nil {
					fmt.Fprintf(stderr, "bad --deadline %q: %v\n", args[i], err)
					return 2
				}
				deadline = d
			}
		case strings.HasPrefix(a, "--deadline="):
			d, err := time.ParseDuration(strings.TrimPrefix(a, "--deadline="))
			if err != nil {
				fmt.Fprintf(stderr, "bad --deadline: %v\n", err)
				return 2
			}
			deadline = d
		case a == "-h" || a == "--help":
			fmt.Fprint(stdout, usage)
			return 0
		default:
			words = append(words, a)
		}
	}

	if showVersion {
		fmt.Fprintf(stdout, "fixpm-probe %s (fixpm %s)\n", version, version)
		return 0
	}

	if !dryRun {
		fmt.Fprint(stderr, usage)
		return 2
	}

	// Same contract as the Python CLI: the environment fallback applies only
	// when no positional words were given at all. Passing an empty string is
	// therefore NOT the same as passing nothing.
	text := ""
	if len(words) > 0 {
		text = strings.TrimSpace(strings.Join(words, " "))
	} else {
		text = strings.TrimSpace(os.Getenv("FIXPM_LAST_COMMAND"))
	}
	if text == "" {
		fmt.Fprintln(stdout, "No command provided.")
		fmt.Fprintln(stdout,
			"Run `fixpm <failed command>` or install a shell hook first: "+
				"`fixpm --init zsh`.")
		return 1
	}

	var spec *ManagerSpec
	if manager != "" {
		spec = SpecForBinary(manager)
		if spec == nil {
			names := map[string]bool{}
			for i := range specs {
				names[specs[i].Binaries[0]] = true
			}
			sorted := make([]string, 0, len(names))
			for n := range names {
				sorted = append(sorted, n)
			}
			sortStrings(sorted)
			fmt.Fprintf(stderr, "unknown manager %q; pick one of: %s\n",
				manager, strings.Join(sorted, ", "))
			return 2
		}
	}

	client := defaultRegistry
	if offline {
		client = NewNpmRegistry(0)
		client.offline = true
	} else if deadline > 0 {
		client = NewNpmRegistry(defaultRegistry.timeout).WithBudget(deadline)
	}

	corrections := GetCorrections(text, spec, client)
	if len(corrections) == 0 {
		fmt.Fprintf(stdout, "No fix found for: %s\n", text)
		return 1
	}
	for _, c := range corrections {
		fmt.Fprintf(stdout, "  [%s] %s\n", KindLabel[c.Kind], c.Command)
	}
	return 0
}
