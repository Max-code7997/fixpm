// Faithful reimplementations of Python semantics that Go's stdlib expresses
// differently. These are needed because fixpm CLI surfaces (scores that decide
// ranking, registry URLs) must be byte-identical across both binaries.
package main

import (
	"math"
	"math/big"
	"strconv"
	"strings"
)

// alwaysSafe is the character set urllib.parse.quote never escapes.
const alwaysSafe = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" +
	"abcdefghijklmnopqrstuvwxyz" +
	"0123456789" +
	"_.-~"

// PyRound mirrors round(x, ndigits) for a float.
//
// CPython rounds the exact binary value of x to the nearest multiple of
// 10**-ndigits, with ties going to the even choice. Go's math.Round is
// half-away-from-zero, which differs on exact ties, so we round exactly using
// rational arithmetic instead of guessing.
func PyRound(x float64, ndigits int) float64 {
	if math.IsNaN(x) || math.IsInf(x, 0) {
		return x
	}
	r := new(big.Rat).SetFloat64(x)
	if r == nil {
		return x
	}
	scale := new(big.Rat).SetInt(pow10(ndigits))
	scaled := new(big.Rat).Mul(r, scale)

	out := new(big.Rat).Quo(new(big.Rat).SetInt(roundHalfEven(scaled)), scale)
	f, _ := out.Float64()
	return f
}

func pow10(n int) *big.Int {
	return new(big.Int).Exp(big.NewInt(10), big.NewInt(int64(n)), nil)
}

// roundHalfEven rounds a rational to the nearest integer, ties to even.
func roundHalfEven(r *big.Rat) *big.Int {
	neg := r.Sign() < 0
	num := new(big.Int).Abs(r.Num())
	den := r.Denom()

	q, rem := new(big.Int).QuoRem(num, den, new(big.Int))
	cmp := new(big.Int).Lsh(rem, 1).Cmp(den)

	up := false
	switch {
	case cmp > 0:
		up = true
	case cmp == 0:
		up = q.Bit(0) == 1 // exact tie -> pick the even neighbour
	}
	if up {
		q.Add(q, big.NewInt(1))
	}
	if neg {
		q.Neg(q)
	}
	return q
}

func percentEncode(b *strings.Builder, c byte) {
	b.WriteByte('%')
	hex := strconv.FormatUint(uint64(c), 16)
	if len(hex) == 1 {
		hex = "0" + hex
	}
	b.WriteString(strings.ToUpper(hex))
}

// PyQuote mirrors urllib.parse.quote(s, safe=extraSafe). Python's quote always
// treats '/' as safe in addition to whatever is passed as `safe`.
func PyQuote(s string, extraSafe string) string {
	var b strings.Builder
	for i := 0; i < len(s); i++ {
		c := s[i]
		if strings.IndexByte(alwaysSafe, c) >= 0 ||
			strings.IndexByte(extraSafe, c) >= 0 {
			b.WriteByte(c)
			continue
		}
		percentEncode(&b, c)
	}
	return b.String()
}

// QuotePlus mirrors urllib.parse.quote_plus: like PyQuote with no extra safe
// characters, except spaces become '+'. This is what urlencode uses for values.
func QuotePlus(s string) string {
	var b strings.Builder
	for i := 0; i < len(s); i++ {
		c := s[i]
		switch {
		case c == ' ':
			b.WriteByte('+')
		case strings.IndexByte(alwaysSafe, c) >= 0:
			b.WriteByte(c)
		default:
			percentEncode(&b, c)
		}
	}
	return b.String()
}
