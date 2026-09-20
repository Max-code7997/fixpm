// String-similarity primitives — port of src/fixpm/distance.py.
//
// Optimal string alignment (restricted Damerau-Levenshtein) so transpositions
// ("svae" -> "save") cost 1, not 2. Kept deliberately identical to the Python
// implementation so both binaries rank candidates the same way.
package main

// runeLen is the Python str length (code points, not bytes). Every place the
// Python code says len(s) for a str must use this, otherwise non-ASCII package
// names score differently in Go than in Python.
func runeLen(s string) int {
	n := 0
	for range s {
		n++
	}
	return n
}

// EditDistance mirrors distance.edit_distance.
func EditDistance(a, b string) int {
	if a == b {
		return 0
	}
	ra := []rune(a)
	rb := []rune(b)
	la, lb := len(ra), len(rb)
	if la == 0 || lb == 0 {
		return la + lb
	}

	var prev2 []int
	prev := make([]int, lb+1)
	for j := range prev {
		prev[j] = j
	}
	for i := 1; i <= la; i++ {
		cur := make([]int, lb+1)
		cur[0] = i
		ca := ra[i-1]
		for j := 1; j <= lb; j++ {
			cost := 1
			if ca == rb[j-1] {
				cost = 0
			}
			v := prev[j] + 1
			if t := cur[j-1] + 1; t < v {
				v = t
			}
			if t := prev[j-1] + cost; t < v {
				v = t
			}
			if prev2 != nil && i > 1 && j > 1 && ca == rb[j-2] && ra[i-2] == rb[j-1] {
				if t := prev2[j-2] + 1; t < v {
					v = t
				}
			}
			cur[j] = v
		}
		prev2, prev = prev, cur
	}
	return prev[lb]
}

// Similarity mirrors distance.similarity: 1.0 means identical.
func Similarity(a, b string) float64 {
	m := runeLen(a)
	if n := runeLen(b); n > m {
		m = n
	}
	if m == 0 {
		return 1.0
	}
	return 1.0 - float64(EditDistance(a, b))/float64(m)
}

type ranked struct {
	name  string
	score float64
}

// Rank mirrors distance.rank: best matches first, ties broken by shorter name
// then lexicographic order. The result is independent of candidate order.
func Rank(target string, candidates []string, top int, minScore float64) []string {
	seen := make(map[string]bool, len(candidates))
	hits := make([]ranked, 0, len(candidates))
	for _, c := range candidates {
		if seen[c] {
			continue
		}
		seen[c] = true
		if s := Similarity(target, c); s >= minScore {
			hits = append(hits, ranked{c, s})
		}
	}
	sortRanked(hits)
	if top < len(hits) {
		hits = hits[:top]
	}
	out := make([]string, 0, len(hits))
	for _, h := range hits {
		out = append(out, h.name)
	}
	return out
}

// sortRanked mirrors Python's `sorted(key=lambda t: (-t[1], len(t[0]), t[0]))`.
func sortRanked(hits []ranked) {
	// insertion sort: n is tiny (vocabulary-sized), and it keeps the ordering
	// rule in one readable place instead of three closures.
	for i := 1; i < len(hits); i++ {
		cur := hits[i]
		j := i - 1
		for j >= 0 && less(cur, hits[j]) {
			hits[j+1] = hits[j]
			j--
		}
		hits[j+1] = cur
	}
}

func less(a, b ranked) bool {
	if a.score != b.score {
		return a.score > b.score
	}
	la, lb := runeLen(a.name), runeLen(b.name)
	if la != lb {
		return la < lb
	}
	return a.name < b.name
}
