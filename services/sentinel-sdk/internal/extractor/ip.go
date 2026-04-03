package extractor

import (
	"net"
	"strings"
)

// ExtractClientIP resolves the real client IP from X-Forwarded-For chain,
// X-Real-IP header, or falls back to RemoteAddr. Handles proxy chains
// by selecting the leftmost non-private IP.
func ExtractClientIP(xForwardedFor, xRealIP, remoteAddr string) string {
	// Priority 1: X-Forwarded-For (leftmost non-private IP)
	if xForwardedFor != "" {
		ips := strings.Split(xForwardedFor, ",")
		for _, ip := range ips {
			ip = strings.TrimSpace(ip)
			parsed := net.ParseIP(ip)
			if parsed != nil && !isPrivateIP(parsed) {
				return ip
			}
		}
		// If all private, return the first one
		if first := strings.TrimSpace(ips[0]); first != "" {
			return first
		}
	}

	// Priority 2: X-Real-IP
	if xRealIP != "" {
		return strings.TrimSpace(xRealIP)
	}

	// Priority 3: RemoteAddr (strip port)
	host, _, err := net.SplitHostPort(remoteAddr)
	if err != nil {
		return remoteAddr
	}
	return host
}

// GeoIPResult holds geolocation data for an IP address
type GeoIPResult struct {
	Country string `json:"country"`
	City    string `json:"city"`
	ASN     int32  `json:"asn"`
	ISP     string `json:"isp"`
	IsVPN   bool   `json:"is_vpn"`
	IsTor   bool   `json:"is_tor"`
	IsProxy bool   `json:"is_proxy"`
}

// LookupGeoIP performs geolocation lookup using MaxMind GeoLite2 database.
// Falls back to empty result if DB unavailable (non-blocking).
func LookupGeoIP(ip string) *GeoIPResult {
	// In production, this would use oschwald/maxminddb-golang
	// For now, return basic result and flag for production integration
	parsed := net.ParseIP(ip)
	if parsed == nil {
		return &GeoIPResult{}
	}

	result := &GeoIPResult{}

	// Detect known Tor exit nodes (simplified — production uses a DB)
	if isTorExitNode(ip) {
		result.IsTor = true
	}

	// Detect known VPN ranges (simplified)
	if isKnownVPN(ip) {
		result.IsVPN = true
	}

	return result
}

// ComputeIPReputation returns a reputation score [0-100] for an IP
// 0 = clean, 100 = known malicious
func ComputeIPReputation(ip string, geo *GeoIPResult) int {
	score := 0

	if geo.IsTor {
		score += 30
	}
	if geo.IsVPN {
		score += 15
	}
	if geo.IsProxy {
		score += 20
	}

	// Additional reputation checks would query threat intel feeds
	return score
}

// isPrivateIP checks if an IP is in a private/reserved range
func isPrivateIP(ip net.IP) bool {
	privateRanges := []string{
		"10.0.0.0/8",
		"172.16.0.0/12",
		"192.168.0.0/16",
		"127.0.0.0/8",
		"::1/128",
		"fc00::/7",
		"fe80::/10",
	}

	for _, cidr := range privateRanges {
		_, network, err := net.ParseCIDR(cidr)
		if err != nil {
			continue
		}
		if network.Contains(ip) {
			return true
		}
	}
	return false
}

// Placeholder — in production, query a Tor exit node list
func isTorExitNode(ip string) bool {
	return false
}

// Placeholder — in production, query VPN provider IP ranges
func isKnownVPN(ip string) bool {
	return false
}
