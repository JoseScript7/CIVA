package extractor

import (
	"crypto/sha256"
	"fmt"
	"sort"
	"strings"
)

// DeviceFingerprint holds the computed fingerprint and its components
type DeviceFingerprint struct {
	Hash       string   `json:"hash"`         // SHA-256 of combined signals
	Components []string `json:"components"`   // What signals contributed
	Stability  float64  `json:"stability"`    // How stable this FP is [0-1]
}

// ComputeDeviceFingerprint generates a device fingerprint from HTTP headers.
// Combines multiple signals into a stable hash that identifies the client device.
func ComputeDeviceFingerprint(headers map[string]string) *DeviceFingerprint {
	fp := &DeviceFingerprint{
		Components: make([]string, 0),
	}

	// Collect fingerprint signals in deterministic order
	signals := make([]string, 0, 10)

	// Core signals (high entropy)
	fingerprintHeaders := []struct {
		header string
		weight float64
	}{
		{"User-Agent", 0.25},
		{"Accept", 0.10},
		{"Accept-Language", 0.15},
		{"Accept-Encoding", 0.10},
		{"Sec-Ch-Ua", 0.15},
		{"Sec-Ch-Ua-Platform", 0.10},
		{"Sec-Ch-Ua-Mobile", 0.05},
		{"Sec-Fetch-Mode", 0.05},
		{"Sec-Fetch-Site", 0.05},
	}

	totalWeight := 0.0
	for _, fh := range fingerprintHeaders {
		val, exists := headers[fh.header]
		if !exists {
			// Try case-insensitive lookup
			for k, v := range headers {
				if strings.EqualFold(k, fh.header) {
					val = v
					exists = true
					break
				}
			}
		}

		if exists && val != "" {
			signals = append(signals, fmt.Sprintf("%s=%s", fh.header, val))
			fp.Components = append(fp.Components, fh.header)
			totalWeight += fh.weight
		}
	}

	// Sort for deterministic hashing
	sort.Strings(signals)

	// Compute SHA-256 hash
	combined := strings.Join(signals, "|")
	hash := sha256.Sum256([]byte(combined))
	fp.Hash = fmt.Sprintf("%x", hash)

	// Stability = proportion of expected signals we could extract
	fp.Stability = totalWeight

	return fp
}

// CompareFingerprints returns a similarity score [0-1] between two fingerprints
func CompareFingerprints(fp1, fp2 *DeviceFingerprint) float64 {
	if fp1.Hash == fp2.Hash {
		return 1.0
	}

	// Component-level comparison for partial matches
	set1 := make(map[string]bool)
	for _, c := range fp1.Components {
		set1[c] = true
	}

	matches := 0
	for _, c := range fp2.Components {
		if set1[c] {
			matches++
		}
	}

	total := len(fp1.Components)
	if len(fp2.Components) > total {
		total = len(fp2.Components)
	}
	if total == 0 {
		return 0
	}

	return float64(matches) / float64(total)
}
