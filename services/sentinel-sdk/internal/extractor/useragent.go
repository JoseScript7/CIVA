package extractor

import (
	"strings"
)

// UAAnalysis contains the parsed user-agent analysis
type UAAnalysis struct {
	Browser    string `json:"browser"`
	Version    string `json:"version"`
	OS         string `json:"os"`
	OSVersion  string `json:"os_version"`
	Device     string `json:"device"`
	IsBot      bool   `json:"is_bot"`
	IsHeadless bool   `json:"is_headless"`
	IsMobile   bool   `json:"is_mobile"`
	RiskSignal string `json:"risk_signal,omitempty"`
}

// knownBotPatterns contains User-Agent substrings that indicate bots/scrapers
var knownBotPatterns = []string{
	"bot", "crawler", "spider", "scraper", "wget", "curl",
	"python-requests", "python-urllib", "httpie", "postman",
	"insomnia", "java/", "go-http-client", "node-fetch",
	"axios", "apache-httpclient", "okhttp", "libwww-perl",
	"mechanize", "scrapy", "phantomjs", "selenium",
	"headlesschrome", "puppeteer", "playwright",
}

// knownHeadlessPatterns indicates headless browser automation
var knownHeadlessPatterns = []string{
	"headlesschrome", "headless", "phantomjs",
	"selenium", "puppeteer", "playwright",
	"electron", "nightmare",
}

// AnalyzeUserAgent performs deep analysis of a User-Agent string
// to detect bots, headless browsers, and automation tools.
func AnalyzeUserAgent(rawUA string) *UAAnalysis {
	analysis := &UAAnalysis{
		Device: "desktop",
	}

	if rawUA == "" {
		analysis.IsBot = true
		analysis.RiskSignal = "empty_user_agent"
		return analysis
	}

	lowerUA := strings.ToLower(rawUA)

	// ---- Bot Detection ----
	for _, pattern := range knownBotPatterns {
		if strings.Contains(lowerUA, pattern) {
			analysis.IsBot = true
			analysis.RiskSignal = "bot_pattern:" + pattern
			break
		}
	}

	// ---- Headless Browser Detection ----
	for _, pattern := range knownHeadlessPatterns {
		if strings.Contains(lowerUA, pattern) {
			analysis.IsHeadless = true
			analysis.RiskSignal = "headless:" + pattern
			break
		}
	}

	// ---- Parse Browser ----
	switch {
	case strings.Contains(lowerUA, "edg/"):
		analysis.Browser = "Edge"
		analysis.Version = extractVersion(rawUA, "Edg/")
	case strings.Contains(lowerUA, "chrome/") && !strings.Contains(lowerUA, "chromium/"):
		analysis.Browser = "Chrome"
		analysis.Version = extractVersion(rawUA, "Chrome/")
	case strings.Contains(lowerUA, "firefox/"):
		analysis.Browser = "Firefox"
		analysis.Version = extractVersion(rawUA, "Firefox/")
	case strings.Contains(lowerUA, "safari/") && !strings.Contains(lowerUA, "chrome/"):
		analysis.Browser = "Safari"
		analysis.Version = extractVersion(rawUA, "Version/")
	default:
		analysis.Browser = "Unknown"
	}

	// ---- Parse OS ----
	switch {
	case strings.Contains(lowerUA, "windows"):
		analysis.OS = "Windows"
	case strings.Contains(lowerUA, "macintosh") || strings.Contains(lowerUA, "mac os"):
		analysis.OS = "macOS"
	case strings.Contains(lowerUA, "linux"):
		analysis.OS = "Linux"
	case strings.Contains(lowerUA, "android"):
		analysis.OS = "Android"
		analysis.IsMobile = true
		analysis.Device = "mobile"
	case strings.Contains(lowerUA, "iphone") || strings.Contains(lowerUA, "ipad"):
		analysis.OS = "iOS"
		analysis.IsMobile = true
		analysis.Device = "mobile"
	}

	// ---- Suspiction Heuristics ----
	// Very short UA strings are suspicious
	if len(rawUA) < 20 {
		analysis.RiskSignal = "suspiciously_short_ua"
	}

	// UA claiming to be a very old browser version
	if analysis.Browser == "Chrome" && analysis.Version != "" {
		// Chrome is currently v120+, anything below 90 is suspicious
		if len(analysis.Version) > 0 && analysis.Version[0] < '9' {
			analysis.RiskSignal = "outdated_browser_version"
		}
	}

	return analysis
}

// extractVersion extracts a version string after a prefix in the UA string
func extractVersion(ua, prefix string) string {
	idx := strings.Index(ua, prefix)
	if idx == -1 {
		return ""
	}

	start := idx + len(prefix)
	end := start
	for end < len(ua) && ua[end] != ' ' && ua[end] != ')' && ua[end] != ';' {
		end++
	}

	return ua[start:end]
}
