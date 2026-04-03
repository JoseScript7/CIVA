package models

import (
	"time"

	"github.com/google/uuid"
)

// SessionEvent represents a single intercepted request with all extracted signals
type SessionEvent struct {
	// Identity
	EventID   string `json:"event_id"`
	SessionID string `json:"session_id"`
	UserID    string `json:"user_id"`
	TimestampUS int64 `json:"timestamp_us"`

	// Network Signals
	ClientIP   string `json:"client_ip"`
	GeoCountry string `json:"geo_country"`
	GeoCity    string `json:"geo_city"`
	GeoASN     int32  `json:"geo_asn"`
	JA3Hash    string `json:"ja3_hash"`

	// Device Signals
	DeviceFP     string `json:"device_fp"`
	UserAgentRaw string `json:"user_agent_raw"`
	IsHeadless   bool   `json:"is_headless"`

	// Velocity Metrics
	ReqPerMin     float64 `json:"req_per_min"`
	ReqPerSec     float64 `json:"req_per_sec"`
	BurstDetected bool    `json:"burst_detected"`

	// Request Context
	HTTPMethod     string `json:"http_method"`
	RequestPath    string `json:"request_path"`
	ResponseCode   int32  `json:"response_code"`
	ResponseTimeUS int64  `json:"response_time_us"`

	// JWT Metadata
	JWTIssuedAt  int64 `json:"jwt_issued_at"`
	JWTExpiresAt int64 `json:"jwt_expires_at"`
	JWTReplay    bool  `json:"jwt_replay"`

	// Tracing
	TraceID string `json:"trace_id"`
	SpanID  string `json:"span_id"`

	// Flexible metadata
	Metadata map[string]string `json:"metadata,omitempty"`
}

// NewSessionEvent creates a new event with generated ID and current timestamp
func NewSessionEvent(sessionID, userID string) *SessionEvent {
	return &SessionEvent{
		EventID:     uuid.Must(uuid.NewV7()).String(),
		SessionID:   sessionID,
		UserID:      userID,
		TimestampUS: time.Now().UnixMicro(),
		Metadata:    make(map[string]string),
	}
}

// RiskScore represents the output of the Behavior Agent
type RiskScore struct {
	EventID          string    `json:"event_id"`
	SessionID        string    `json:"session_id"`
	UserID           string    `json:"user_id"`
	TimestampUS      int64     `json:"timestamp_us"`
	RawAnomalyScore  float64   `json:"raw_anomaly_score"`
	NormalizedScore  float64   `json:"normalized_score"`
	BaselineAdjusted float64   `json:"baseline_adjusted"`
	FinalRiskScore   float64   `json:"final_risk_score"`
	FeatureVector    []float64 `json:"feature_vector"`
	AnomalyFlags     []string  `json:"anomaly_flags"`
	AnomalyCategory  string    `json:"anomaly_category"`
	Confidence       float64   `json:"confidence"`
	InferenceTimeUS  int64     `json:"inference_time_us"`
	ModelVersion     string    `json:"model_version"`
	TraceID          string    `json:"trace_id"`
	SpanID           string    `json:"span_id"`
}

// ActionType defines the possible orchestrator actions
type ActionType int

const (
	ActionSilentAllow       ActionType = 0
	ActionMFAChallenge      ActionType = 1
	ActionActivateDeception ActionType = 2
	ActionKillSession       ActionType = 3
)

// String returns human-readable action name
func (a ActionType) String() string {
	switch a {
	case ActionSilentAllow:
		return "SILENT_ALLOW"
	case ActionMFAChallenge:
		return "MFA_CHALLENGE"
	case ActionActivateDeception:
		return "ACTIVATE_DECEPTION"
	case ActionKillSession:
		return "KILL_SESSION"
	default:
		return "UNKNOWN"
	}
}
