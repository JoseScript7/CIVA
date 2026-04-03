package main

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/civa-platform/sentinel-sdk/internal/config"
	"github.com/civa-platform/sentinel-sdk/internal/extractor"
	"github.com/civa-platform/sentinel-sdk/internal/middleware"
	"github.com/civa-platform/sentinel-sdk/internal/publisher"
	"go.uber.org/zap"
)

const (
	version = "1.0.0"
	service = "sentinel-sdk"
	banner  = `
   _____ _____ _   _ _____ _____ _   _ _____ _     
  / ____|  ___| \ | |_   _|_   _| \ | |  ___| |    
  | (__ | |__ |  \| | | |   | | |  \| | |__ | |    
   \___ \|  __|| .   | | |   | | | .   |  __|| |    
   ____) | |___| |\  | | |  _| |_| |\  | |___| |____
  |_____/|_____|_| \_| |_| |_____|_| \_|_____|______|
                                  CIVA Security Platform
                                  Edge Signal Extraction
`
)

var startTime = time.Now()

func main() {
	fmt.Print(banner)

	// ---- Load Configuration ----
	cfg := config.Load()

	// ---- Initialize Logger ----
	var logger *zap.Logger
	var err error
	if cfg.LogLevel == "debug" {
		logger, err = zap.NewDevelopment()
	} else {
		logger, err = zap.NewProduction()
	}
	if err != nil {
		fmt.Fprintf(os.Stderr, "Failed to initialize logger: %v\n", err)
		os.Exit(1)
	}
	defer logger.Sync()

	logger.Info("Starting Sentinel SDK",
		zap.String("version", version),
		zap.Int("port", cfg.Port),
	)

	// ---- Initialize Kafka Publisher ----
	kafkaPublisher, err := publisher.NewKafkaPublisher(
		cfg.KafkaBootstrapServers,
		cfg.KafkaSessionTopic,
		logger,
	)
	if err != nil {
		logger.Fatal("Failed to initialize Kafka publisher", zap.Error(err))
	}
	defer kafkaPublisher.Close()

	// ---- Initialize Velocity Tracker (Redis) ----
	var velocityTracker *extractor.VelocityTracker
	velocityTracker, err = extractor.NewVelocityTracker(
		cfg.RedisURL,
		cfg.RedisVelocityWindow,
		float64(cfg.RedisVelocityMaxReqs),
	)
	if err != nil {
		logger.Warn("Velocity tracker unavailable — running without request velocity",
			zap.Error(err),
		)
	} else {
		defer velocityTracker.Close()
	}

	// ---- Create Interceptor Middleware ----
	interceptor := middleware.NewSentinelInterceptor(logger, kafkaPublisher, velocityTracker)

	// ---- Define Routes ----
	mux := http.NewServeMux()

	// Health check endpoint
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"status":  "healthy",
			"service": service,
			"version": version,
			"uptime":  time.Since(startTime).String(),
		})
	})

	// Readiness check
	mux.HandleFunc("/ready", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		ready := true
		checks := map[string]string{"kafka": "ok"}
		if velocityTracker != nil {
			checks["redis"] = "ok"
		} else {
			checks["redis"] = "unavailable"
			ready = false
		}
		status := http.StatusOK
		if !ready {
			status = http.StatusServiceUnavailable
		}
		w.WriteHeader(status)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"ready":  ready,
			"checks": checks,
		})
	})

	// Metrics endpoint (Prometheus format)
	mux.HandleFunc("/metrics", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/plain")
		fmt.Fprintf(w, "# HELP sentinel_requests_total Total intercepted requests\n")
		fmt.Fprintf(w, "# TYPE sentinel_requests_total counter\n")
		fmt.Fprintf(w, "sentinel_requests_total 0\n")
	})

	// Default handler
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]interface{}{
			"service": service,
			"message": "Sentinel SDK is intercepting traffic",
			"path":    r.URL.Path,
		})
	})

	// Wrap all routes with the interceptor middleware
	handler := interceptor.Intercept(mux)

	// ---- Start Server ----
	server := &http.Server{
		Addr:         fmt.Sprintf(":%d", cfg.Port),
		Handler:      handler,
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 10 * time.Second,
		IdleTimeout:  120 * time.Second,
	}

	// Graceful shutdown
	go func() {
		sigCh := make(chan os.Signal, 1)
		signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
		sig := <-sigCh
		logger.Info("Received shutdown signal", zap.String("signal", sig.String()))

		shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()

		if err := server.Shutdown(shutdownCtx); err != nil {
			logger.Error("Server shutdown error", zap.Error(err))
		}
	}()

	logger.Info("Sentinel SDK listening",
		zap.String("addr", server.Addr),
		zap.String("version", version),
	)

	if err := server.ListenAndServe(); err != http.ErrServerClosed {
		logger.Fatal("Server failed", zap.Error(err))
	}

	logger.Info("Sentinel SDK stopped gracefully")
}
