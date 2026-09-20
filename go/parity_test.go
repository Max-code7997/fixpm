package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

type vectorDocument struct {
	Comment string   `json:"comment"`
	Vectors []vector `json:"vectors"`
}

type vector struct {
	Args   []string `json:"args"`
	Exit   int      `json:"exit"`
	Stdout string   `json:"stdout"`
}

func loadVectors(t *testing.T) []vector {
	t.Helper()
	raw, err := os.ReadFile(filepath.Join("testdata", "parity.json"))
	if err != nil {
		t.Fatalf("read parity vectors (run scripts/gen_parity_vectors.py): %v", err)
	}
	var doc vectorDocument
	if err := json.Unmarshal(raw, &doc); err != nil {
		t.Fatalf("parse parity vectors: %v", err)
	}
	if len(doc.Vectors) == 0 {
		t.Fatal("parity vector file is empty")
	}
	return doc.Vectors
}

// TestParityWithPythonReference replays golden vectors captured from the real
// Python CLI (scripts/gen_parity_vectors.py runs `python -m fixpm` and records
// its bytes) and requires the probe to produce identical stdout and exit code.
//
// This is the guard rail for the whole port: if the two implementations ever
// disagree about a command, this fails with the exact diff.
func TestParityWithPythonReference(t *testing.T) {
	for i, v := range loadVectors(t) {
		// --offline keeps the run hermetic; the generator proves every vector
		// is network-free, so it cannot change the expected result.
		args := append([]string{"--offline"}, v.Args...)

		var stdout, stderr bytes.Buffer
		code := run(args, &stdout, &stderr)

		if code != v.Exit {
			t.Errorf("vector %d %q: exit = %d, want %d (stderr: %s)",
				i, v.Args, code, v.Exit, stderr.String())
		}
		if got := stdout.String(); got != v.Stdout {
			t.Errorf("vector %d %q:\n  got  %q\n  want %q",
				i, v.Args, got, v.Stdout)
		}
	}
}

// TestOutputUsesLFEverywhere documents the one deliberate byte-level deviation
// from the Python CLI.
//
// Python's text-mode stdout translates "\n" to os.linesep, so on Windows the
// reference implementation emits CRLF while the probe emits LF. The generator
// normalises vectors to LF for this reason. LF is the intentional choice here:
// the probe is the Unix-shell hook path, and mixed line endings are a liability
// for anything that later pipes or diffs the output.
func TestOutputUsesLFEverywhere(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := run([]string{"--offline", "--dry-run", "npm isntall react"},
		&stdout, &stderr)
	if code != 0 {
		t.Fatalf("exit = %d, want 0", code)
	}
	if strings.Contains(stdout.String(), "\r") {
		t.Errorf("probe output contains a carriage return: %q", stdout.String())
	}
	if !strings.HasSuffix(stdout.String(), "\n") {
		t.Errorf("probe output should end with LF: %q", stdout.String())
	}
}

// TestRuneLengthNotByteLength pins the one place a naive port silently
// diverges: Python's len() on a str counts code points, Go's len() counts bytes.
func TestRuneLengthNotByteLength(t *testing.T) {
	// "lodash" vs "lodäsh" differ by one substitution over six code points, so
	// similarity must be 5/6. A byte-oriented implementation would see "ä" as
	// two bytes and compute a different distance.
	if got := Similarity("lodash", "lodäsh"); got < 0.83 || got > 0.84 {
		t.Errorf("Similarity(lodash, lodäsh) = %v, want ~0.833", got)
	}
}
