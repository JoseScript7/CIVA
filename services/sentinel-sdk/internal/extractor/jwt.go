package extractor

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"strings"
	"time"
)

// JWTClaims represents the extracted claims from a JWT token
type JWTClaims struct {
	Subject   string `json:"sub"`
	Issuer    string `json:"iss"`
	SessionID string `json:"session_id"`
	IssuedAt  int64  `json:"iat"`
	ExpiresAt int64  `json:"exp"`
	JTI       string `json:"jti"` // JWT ID for replay detection
}

// JWTAnalysis is the result of JWT introspection
type JWTAnalysis struct {
	Claims    *JWTClaims `json:"claims"`
	IsValid   bool       `json:"is_valid"`
	IsExpired bool       `json:"is_expired"`
	IsReplay  bool       `json:"is_replay"`
	TokenAge  int64      `json:"token_age_s"`    // Seconds since issuance
	ClockSkew int64      `json:"clock_skew_ms"`  // Clock skew in milliseconds
	Error     string     `json:"error,omitempty"`
}

// AnalyzeJWT performs JWT introspection without full cryptographic validation
// (that's the auth service's job). Instead, we extract signals for anomaly detection.
func AnalyzeJWT(authHeader string) *JWTAnalysis {
	analysis := &JWTAnalysis{}

	// Extract token from "Bearer <token>" header
	token := extractBearerToken(authHeader)
	if token == "" {
		analysis.Error = "no_bearer_token"
		return analysis
	}

	// Decode JWT payload (without signature verification — that's the auth layer's job)
	claims, err := decodeJWTPayload(token)
	if err != nil {
		analysis.Error = "decode_failed: " + err.Error()
		return analysis
	}

	analysis.Claims = claims
	now := time.Now().Unix()

	// Check expiration
	if claims.ExpiresAt > 0 && now > claims.ExpiresAt {
		analysis.IsExpired = true
	}

	// Calculate token age
	if claims.IssuedAt > 0 {
		analysis.TokenAge = now - claims.IssuedAt
	}

	// Detect clock skew — if iat is in the future, there's a skew
	if claims.IssuedAt > 0 && claims.IssuedAt > now {
		analysis.ClockSkew = (claims.IssuedAt - now) * 1000
	}

	// Replay detection is handled via Redis JTI store (see middleware layer)
	analysis.IsValid = !analysis.IsExpired
	return analysis
}

// ComputeJWTHMAC generates an HMAC of the JWT for integrity tracking
func ComputeJWTHMAC(token string, secret []byte) string {
	mac := hmac.New(sha256.New, secret)
	mac.Write([]byte(token))
	return base64.URLEncoding.EncodeToString(mac.Sum(nil))
}

// extractBearerToken extracts the raw JWT from an Authorization header
func extractBearerToken(authHeader string) string {
	if authHeader == "" {
		return ""
	}
	parts := strings.SplitN(authHeader, " ", 2)
	if len(parts) != 2 || !strings.EqualFold(parts[0], "bearer") {
		return ""
	}
	return strings.TrimSpace(parts[1])
}

// decodeJWTPayload decodes the JWT payload without signature verification
func decodeJWTPayload(token string) (*JWTClaims, error) {
	parts := strings.Split(token, ".")
	if len(parts) != 3 {
		return nil, &JWTError{Message: "invalid JWT format: expected 3 parts"}
	}

	// Decode base64url payload
	payload := parts[1]
	// Add padding if needed
	switch len(payload) % 4 {
	case 2:
		payload += "=="
	case 3:
		payload += "="
	}

	decoded, err := base64.URLEncoding.DecodeString(payload)
	if err != nil {
		return nil, &JWTError{Message: "base64 decode failed: " + err.Error()}
	}

	var claims JWTClaims
	if err := json.Unmarshal(decoded, &claims); err != nil {
		return nil, &JWTError{Message: "JSON unmarshal failed: " + err.Error()}
	}

	return &claims, nil
}

// JWTError represents a JWT-specific error
type JWTError struct {
	Message string
}

func (e *JWTError) Error() string {
	return e.Message
}
