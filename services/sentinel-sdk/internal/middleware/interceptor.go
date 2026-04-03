package middleware

import (
	"context"
	"net/http"
	"sync"
	"time"

	"github.com/civa-platform/sentinel-sdk/internal/extractor"
	"github.com/civa-platform/sentinel-sdk/internal/publisher"
	"github.com/civa-platform/sentinel-sdk/pkg/models"
	"go.uber.org/zap"
)

// SentinelInterceptor is the core HTTP middleware that extracts signals
// from every request and publishes them to Kafka.
type SentinelInterceptor struct {
	logger          *zap.Logger
	kafkaPublisher  publisher.EventPublisher
	velocityTracker *extractor.VelocityTracker
	mu              sync.RWMutex
}

// NewSentinelInterceptor creates a new interceptor instance
func NewSentinelInterceptor(
	logger *zap.Logger,
	kp publisher.EventPublisher,
	vt *extractor.VelocityTracker,
) *SentinelInterceptor {
	return &SentinelInterceptor{
		logger:          logger,
		kafkaPublisher:  kp,
		velocityTracker: vt,
	}
}

// Intercept returns an http.Handler middleware that extracts signals and publishes events
func (si *SentinelInterceptor) Intercept(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		startTime := time.Now()
		ctx := r.Context()

		// Wrap response writer to capture status code
		rw := &responseCapture{ResponseWriter: w, statusCode: 200}

		// Extract session and user from JWT (non-blocking)
		jwtAnalysis := extractor.AnalyzeJWT(r.Header.Get("Authorization"))

		sessionID := ""
		userID := ""
		if jwtAnalysis.Claims != nil {
			sessionID = jwtAnalysis.Claims.SessionID
			userID = jwtAnalysis.Claims.Subject
		}

		// Create event shell
		event := models.NewSessionEvent(sessionID, userID)

		// ---- Parallel Signal Extraction ----
		var wg sync.WaitGroup
		wg.Add(4)

		// 1. IP + GeoIP (goroutine)
		go func() {
			defer wg.Done()
			ip := extractor.ExtractClientIP(
				r.Header.Get("X-Forwarded-For"),
				r.Header.Get("X-Real-IP"),
				r.RemoteAddr,
			)
			event.ClientIP = ip

			geo := extractor.LookupGeoIP(ip)
			event.GeoCountry = geo.Country
			event.GeoCity = geo.City
			event.GeoASN = geo.ASN
		}()

		// 2. Device Fingerprint (goroutine)
		go func() {
			defer wg.Done()
			headers := make(map[string]string)
			for key := range r.Header {
				headers[key] = r.Header.Get(key)
			}
			fp := extractor.ComputeDeviceFingerprint(headers)
			event.DeviceFP = fp.Hash
		}()

		// 3. User-Agent Analysis (goroutine)
		go func() {
			defer wg.Done()
			ua := extractor.AnalyzeUserAgent(r.Header.Get("User-Agent"))
			event.UserAgentRaw = r.Header.Get("User-Agent")
			event.IsHeadless = ua.IsHeadless
		}()

		// 4. Velocity Tracking (goroutine)
		go func() {
			defer wg.Done()
			if si.velocityTracker != nil && sessionID != "" {
				vel, err := si.velocityTracker.Track(ctx, sessionID)
				if err != nil {
					si.logger.Warn("velocity tracking failed", zap.Error(err))
					return
				}
				event.ReqPerMin = vel.RequestsPerMinute
				event.ReqPerSec = vel.RequestsPerSecond
				event.BurstDetected = vel.BurstDetected
			}
		}()

		// Wait for all extractors (should complete in < 2ms total)
		wg.Wait()

		// ---- JWT Metadata ----
		if jwtAnalysis.Claims != nil {
			event.JWTIssuedAt = jwtAnalysis.Claims.IssuedAt
			event.JWTExpiresAt = jwtAnalysis.Claims.ExpiresAt
			event.JWTReplay = jwtAnalysis.IsReplay
		}

		// ---- Request Context ----
		event.HTTPMethod = r.Method
		event.RequestPath = r.URL.Path

		// ---- Execute the actual handler ----
		next.ServeHTTP(rw, r)

		// ---- Post-handler capture ----
		event.ResponseCode = int32(rw.statusCode)
		event.ResponseTimeUS = time.Since(startTime).Microseconds()

		// ---- Publish to Kafka (async, non-blocking) ----
		go func() {
			pubCtx, cancel := context.WithTimeout(context.Background(), 100*time.Millisecond)
			defer cancel()

			if err := si.kafkaPublisher.Publish(pubCtx, event); err != nil {
				si.logger.Error("failed to publish session event",
					zap.String("session_id", event.SessionID),
					zap.Error(err),
				)
			}
		}()
	})
}

// responseCapture wraps http.ResponseWriter to capture the status code
type responseCapture struct {
	http.ResponseWriter
	statusCode int
	written    bool
}

func (rw *responseCapture) WriteHeader(code int) {
	if !rw.written {
		rw.statusCode = code
		rw.written = true
	}
	rw.ResponseWriter.WriteHeader(code)
}

func (rw *responseCapture) Write(b []byte) (int, error) {
	if !rw.written {
		rw.statusCode = 200
		rw.written = true
	}
	return rw.ResponseWriter.Write(b)
}
