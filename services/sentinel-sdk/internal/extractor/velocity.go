package extractor

import (
	"context"
	"fmt"
	"strconv"
	"time"

	"github.com/redis/go-redis/v9"
)

// VelocityResult holds the computed velocity metrics for a session
type VelocityResult struct {
	RequestsPerMinute float64 `json:"req_per_min"`
	RequestsPerSecond float64 `json:"req_per_sec"`
	BurstDetected     bool    `json:"burst_detected"`
	WindowSize        int64   `json:"window_size_sec"`
	TotalInWindow     int64   `json:"total_in_window"`
}

// VelocityTracker uses Redis sorted sets to compute request velocity
// with a sliding window approach.
type VelocityTracker struct {
	client         *redis.Client
	windowDuration time.Duration
	burstThreshold float64 // Requests per second threshold for burst detection
}

// NewVelocityTracker creates a new velocity tracker backed by Redis
func NewVelocityTracker(redisURL string, windowDuration time.Duration, burstThreshold float64) (*VelocityTracker, error) {
	opts, err := redis.ParseURL(redisURL)
	if err != nil {
		return nil, fmt.Errorf("parse redis url: %w", err)
	}

	client := redis.NewClient(opts)

	// Verify connection
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()
	if err := client.Ping(ctx).Err(); err != nil {
		return nil, fmt.Errorf("redis ping: %w", err)
	}

	return &VelocityTracker{
		client:         client,
		windowDuration: windowDuration,
		burstThreshold: burstThreshold,
	}, nil
}

// Track records a request and computes current velocity metrics.
// Uses Redis ZADD + ZRANGEBYSCORE for O(log N) sliding window.
func (vt *VelocityTracker) Track(ctx context.Context, sessionID string) (*VelocityResult, error) {
	now := time.Now()
	nowMicro := float64(now.UnixMicro())
	windowStart := float64(now.Add(-vt.windowDuration).UnixMicro())

	key := fmt.Sprintf("velocity:%s", sessionID)

	// Pipeline: add current request + remove old entries + count
	pipe := vt.client.Pipeline()

	// Add current timestamp as both score and member (micro precision)
	pipe.ZAdd(ctx, key, redis.Z{
		Score:  nowMicro,
		Member: strconv.FormatFloat(nowMicro, 'f', 0, 64),
	})

	// Remove entries outside the window
	pipe.ZRemRangeByScore(ctx, key, "-inf", strconv.FormatFloat(windowStart, 'f', 0, 64))

	// Count entries in window
	countCmd := pipe.ZCard(ctx, key)

	// Set TTL on the key (auto-cleanup)
	pipe.Expire(ctx, key, vt.windowDuration*2)

	// Get last 5 entries for burst detection
	recentCmd := pipe.ZRevRangeWithScores(ctx, key, 0, 4)

	_, err := pipe.Exec(ctx)
	if err != nil {
		return nil, fmt.Errorf("redis pipeline: %w", err)
	}

	totalInWindow := countCmd.Val()
	windowSec := vt.windowDuration.Seconds()

	result := &VelocityResult{
		RequestsPerMinute: float64(totalInWindow) / windowSec * 60,
		RequestsPerSecond: float64(totalInWindow) / windowSec,
		WindowSize:        int64(windowSec),
		TotalInWindow:     totalInWindow,
	}

	// Burst detection: check if last 5 requests happened within 1 second
	recent := recentCmd.Val()
	if len(recent) >= 5 {
		oldest := recent[len(recent)-1].Score
		newest := recent[0].Score
		timeDiffSec := (newest - oldest) / 1_000_000 // microseconds to seconds
		if timeDiffSec > 0 {
			instantRate := float64(len(recent)) / timeDiffSec
			if instantRate > vt.burstThreshold {
				result.BurstDetected = true
			}
		}
	}

	return result, nil
}

// GetVelocity returns current velocity without recording a new request
func (vt *VelocityTracker) GetVelocity(ctx context.Context, sessionID string) (*VelocityResult, error) {
	now := time.Now()
	windowStart := float64(now.Add(-vt.windowDuration).UnixMicro())

	key := fmt.Sprintf("velocity:%s", sessionID)

	count, err := vt.client.ZCount(ctx, key, strconv.FormatFloat(windowStart, 'f', 0, 64), "+inf").Result()
	if err != nil {
		return nil, fmt.Errorf("redis zcount: %w", err)
	}

	windowSec := vt.windowDuration.Seconds()
	return &VelocityResult{
		RequestsPerMinute: float64(count) / windowSec * 60,
		RequestsPerSecond: float64(count) / windowSec,
		WindowSize:        int64(windowSec),
		TotalInWindow:     count,
	}, nil
}

// Close closes the Redis connection
func (vt *VelocityTracker) Close() error {
	return vt.client.Close()
}
