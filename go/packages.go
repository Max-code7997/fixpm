// npm registry client with graceful offline degradation — port of
// src/fixpm/packages.py.
//
// Network behaviour deliberately differs from the Python original in one way:
// weekly-download lookups are fetched concurrently and bounded by a deadline,
// because fixpm runs from a prompt hook and the Python version issues up to
// five serial HTTPS requests before the prompt can redraw.
package main

import (
	"context"
	"encoding/json"
	"io"
	"math"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"
)

// Suggestion mirrors fixpm.packages.Suggestion.
type Suggestion struct {
	Name            string
	WeeklyDownloads int64 // 0 when unknown
	Score           float64
}

// baseName mirrors packages.base_name: strip a trailing version specifier, but
// keep a bare scope prefix ("@scope/pkg" has no version to strip).
func baseName(spec string) string {
	if i := strings.LastIndex(spec, "@"); i > 0 {
		return spec[:i]
	}
	return spec
}

// formatDownloads mirrors packages.format_downloads.
func formatDownloads(n int64) string {
	switch {
	case n >= 1_000_000:
		return formatFloat(float64(n)/1_000_000, 1) + "M"
	case n >= 1_000:
		return formatFloat(float64(n)/1_000, 0) + "k"
	default:
		return itoa(n)
	}
}

// NpmRegistry mirrors packages.NpmRegistry, plus a total time budget.
type NpmRegistry struct {
	timeout time.Duration // per-request ceiling
	budget  time.Duration // whole-run ceiling; 0 means unlimited
	started time.Time

	mu      sync.Mutex
	cache   map[string]any
	offline bool // circuit breaker after repeated failures
}

// NewNpmRegistry mirrors NpmRegistry(timeout=2.5).
func NewNpmRegistry(timeout time.Duration) *NpmRegistry {
	return &NpmRegistry{
		timeout: timeout,
		started: time.Now(),
		cache:   map[string]any{},
	}
}

// WithBudget bounds all registry access to *budget* in total.
//
// This exists because fixpm runs from a prompt hook: the Python original can
// issue up to five serial 2.5s requests before the prompt redraws. A budget
// caps that. Once it is spent, lookups degrade to the offline path instead of
// stalling the shell.
func (r *NpmRegistry) WithBudget(budget time.Duration) *NpmRegistry {
	r.budget = budget
	r.started = time.Now()
	return r
}

// remaining returns the per-request timeout to use, or false when the budget
// is already spent.
func (r *NpmRegistry) remaining() (time.Duration, bool) {
	if r.budget <= 0 {
		return r.timeout, true
	}
	left := r.budget - time.Since(r.started)
	if left <= 0 {
		return 0, false
	}
	if r.timeout > 0 && left > r.timeout {
		left = r.timeout
	}
	return left, true
}

func (r *NpmRegistry) markFailure() {
	r.mu.Lock()
	defer r.mu.Unlock()
	// Nothing ever succeeded -> stop trying for the rest of the process.
	if len(r.cache) == 0 {
		r.offline = true
	}
}

// getJSON mirrors NpmRegistry._get_json.
func (r *NpmRegistry) getJSON(rawURL string) any {
	r.mu.Lock()
	if r.offline {
		r.mu.Unlock()
		return nil
	}
	if v, ok := r.cache[rawURL]; ok {
		r.mu.Unlock()
		return v
	}
	r.mu.Unlock()

	perRequest, ok := r.remaining()
	if !ok {
		return nil // budget spent: degrade instead of stalling the prompt
	}

	ctx, cancel := context.WithTimeout(context.Background(), perRequest)
	defer cancel()

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, rawURL, nil)
	if err != nil {
		r.markFailure()
		return nil
	}
	req.Header.Set("User-Agent", userAgent)
	req.Header.Set("Accept", "application/json")

	client := &http.Client{Timeout: perRequest}
	resp, err := client.Do(req)
	if err != nil {
		r.markFailure()
		return nil
	}
	defer func() { _ = resp.Body.Close() }()

	if resp.StatusCode >= 400 {
		// Python's urlopen raises HTTPError here, which _get_json catches.
		r.markFailure()
		return nil
	}
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		r.markFailure()
		return nil
	}
	var data any
	if err := json.Unmarshal(body, &data); err != nil {
		r.markFailure()
		return nil
	}

	r.mu.Lock()
	if len(r.cache) > 256 {
		r.cache = map[string]any{}
	}
	r.cache[rawURL] = data
	r.mu.Unlock()
	return data
}

// search mirrors NpmRegistry.search.
func (r *NpmRegistry) search(name string, size int) []string {
	q := url.Values{}
	q.Set("text", name)
	q.Set("size", itoa(int64(size)))
	rawURL := searchURL + "?" + q.Encode()

	data := r.getJSON(rawURL)
	names := []string{}
	root, ok := data.(map[string]any)
	if !ok {
		return names
	}
	objects, ok := root["objects"].([]any)
	if !ok {
		return names
	}
	for _, item := range objects {
		obj, ok := item.(map[string]any)
		if !ok {
			continue
		}
		pkg, ok := obj["package"].(map[string]any)
		if !ok {
			continue
		}
		if name, ok := pkg["name"].(string); ok {
			names = append(names, name)
		}
	}
	return names
}

// weeklyDownloads mirrors NpmRegistry.weekly_downloads, but issues the lookups
// concurrently so the whole batch costs one round trip instead of N.
func (r *NpmRegistry) weeklyDownloads(names []string) map[string]int64 {
	out := make(map[string]int64, len(names))
	var mu sync.Mutex
	var wg sync.WaitGroup

	for _, name := range names {
		wg.Add(1)
		go func(name string) {
			defer wg.Done()
			rawURL := strings.ReplaceAll(downloadURL, "{pkg}", PyQuote(name, "@"))
			data := r.getJSON(rawURL)

			mu.Lock()
			defer mu.Unlock()
			root, ok := data.(map[string]any)
			if !ok {
				return
			}
			if v, ok := root["downloads"]; ok {
				if f, ok := v.(float64); ok { // encoding/json decodes numbers as float64
					out[name] = int64(f)
				}
			}
		}(name)
	}
	wg.Wait()
	return out
}

// Suggest mirrors NpmRegistry.suggest.
func (r *NpmRegistry) Suggest(name string, limit int) []Suggestion {
	target := strings.ToLower(baseName(name))

	// Curated map wins first: npm search has poor recall for misspelled
	// queries, so classic typos must not depend on the network at all.
	if curated, ok := popularFallback[target]; ok {
		return []Suggestion{{Name: curated, WeeklyDownloads: 0, Score: 0.95}}
	}

	registryNames := r.search(target, 8)
	if len(registryNames) > 5 {
		registryNames = registryNames[:5]
	}
	for _, n := range registryNames {
		if strings.ToLower(n) == target {
			return nil // exact hit: the name was fine, a rename can't be the fix
		}
	}

	downloads := r.weeklyDownloads(registryNames)

	corpusHits := []string{}
	for _, p := range popularPackages {
		if Similarity(target, strings.ToLower(p)) >= 0.5 {
			corpusHits = append(corpusHits, p)
			if len(corpusHits) == 3 {
				break
			}
		}
	}

	type entry struct {
		name       string
		fromCorpus bool
	}
	entries := make([]entry, 0, len(registryNames)+len(corpusHits))
	for _, n := range registryNames {
		entries = append(entries, entry{n, false})
	}
	for _, p := range corpusHits {
		entries = append(entries, entry{p, true})
	}

	logScale := math.Log1p(3_000_000)
	scored := []Suggestion{}
	seen := map[string]bool{}
	for _, e := range entries {
		low := strings.ToLower(e.name)
		if low == target || seen[low] {
			continue // exact match means the name was fine; no rename fix
		}
		seen[low] = true

		sim := Similarity(target, low)
		if sim < 0.4 {
			continue
		}

		dl, hasDL := downloads[e.name]
		var pop float64
		if hasDL {
			pop = math.Min(1.0, math.Log1p(float64(dl))/logScale)
		} else {
			dl = 0
			if e.fromCorpus {
				pop = corpusPopPrior
			}
		}

		s := Suggestion{
			Name:            e.name,
			WeeklyDownloads: dl,
			Score:           PyRound(0.8*sim+0.2*pop, 3),
		}
		if s.Score >= 0.4 {
			scored = append(scored, s)
		}
	}

	sortSuggestions(scored)
	if len(scored) > limit {
		scored = scored[:limit]
	}
	return scored
}
