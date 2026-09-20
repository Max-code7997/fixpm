// Small helpers shared by the ported modules.
package main

import (
	"sort"
	"strconv"
)

// formatFloat mirrors Python's f"{v:.{prec}f}".
func formatFloat(v float64, prec int) string {
	return strconv.FormatFloat(v, 'f', prec, 64)
}

// itoa is a short alias so the ported bodies stay close to the Python source.
func itoa(n int64) string {
	return strconv.FormatInt(n, 10)
}

// sortStrings sorts in place.
func sortStrings(items []string) {
	sort.Strings(items)
}

// sortSuggestions mirrors `scored.sort(key=lambda s: (-s.score, s.name))`.
func sortSuggestions(items []Suggestion) {
	sort.SliceStable(items, func(i, j int) bool {
		if items[i].Score != items[j].Score {
			return items[i].Score > items[j].Score
		}
		return items[i].Name < items[j].Name
	})
}
