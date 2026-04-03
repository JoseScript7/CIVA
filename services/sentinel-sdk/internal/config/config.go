package config

import (
	"os"
	"strconv"
	"strings"
	"time"
)

// Config holds all Sentinel SDK configuration
type Config struct {
	// Server
	Port     int
	LogLevel string

	// Kafka
	KafkaBootstrapServers string
	KafkaSessionTopic     string
	KafkaProducerTimeout  time.Duration

	// Redis
	RedisURL             string
	RedisPassword        string
	RedisVelocityWindow  time.Duration
	RedisVelocityMaxReqs int

	// GeoIP
	GeoIPDBPath string

	// JWT
	JWTSigningKeys []string

	// Circuit Breaker
	CBMaxFailures    int
	CBTimeout        time.Duration
	CBHalfOpenMaxReqs int

	// OpenTelemetry
	OTELEndpoint    string
	OTELServiceName string
}

// Load creates a Config from environment variables with sensible defaults
func Load() *Config {
	return &Config{
		Port:     getEnvInt("SENTINEL_PORT", 8001),
		LogLevel: getEnv("SENTINEL_LOG_LEVEL", "info"),

		KafkaBootstrapServers: getEnv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
		KafkaSessionTopic:     getEnv("KAFKA_SESSION_TOPIC", "session.events"),
		KafkaProducerTimeout:  time.Duration(getEnvInt("KAFKA_PRODUCER_TIMEOUT_MS", 100)) * time.Millisecond,

		RedisURL:             getEnv("REDIS_URL", "redis://localhost:6379/0"),
		RedisPassword:        getEnv("REDIS_PASSWORD", ""),
		RedisVelocityWindow:  time.Duration(getEnvInt("REDIS_VELOCITY_WINDOW_SEC", 60)) * time.Second,
		RedisVelocityMaxReqs: getEnvInt("REDIS_VELOCITY_MAX_REQS", 100),

		GeoIPDBPath: getEnv("SENTINEL_GEOIP_DB_PATH", "/data/GeoLite2-City.mmdb"),

		JWTSigningKeys: strings.Split(getEnv("JWT_SIGNING_KEYS", ""), ","),

		CBMaxFailures:     getEnvInt("CB_MAX_FAILURES", 5),
		CBTimeout:         time.Duration(getEnvInt("CB_TIMEOUT_SEC", 30)) * time.Second,
		CBHalfOpenMaxReqs: getEnvInt("CB_HALF_OPEN_MAX_REQS", 3),

		OTELEndpoint:    getEnv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
		OTELServiceName: getEnv("OTEL_SERVICE_NAME", "sentinel-sdk"),
	}
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func getEnvInt(key string, fallback int) int {
	if v := os.Getenv(key); v != "" {
		if i, err := strconv.Atoi(v); err == nil {
			return i
		}
	}
	return fallback
}
