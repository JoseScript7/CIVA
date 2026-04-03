package middleware

import (
	"sync"
	"time"
)

// CircuitState represents the current state of the circuit breaker
type CircuitState int

const (
	StateClosed   CircuitState = iota // Normal — requests flow through
	StateOpen                         // Tripped — requests are rejected
	StateHalfOpen                     // Testing — limited requests allowed
)

// CircuitBreaker implements the circuit breaker pattern for downstream
// dependencies (Kafka, Redis) to prevent cascade failures.
type CircuitBreaker struct {
	mu              sync.RWMutex
	state           CircuitState
	failures        int
	successes       int
	maxFailures     int
	timeout         time.Duration
	halfOpenMaxReqs int
	lastFailure     time.Time
	onStateChange   func(from, to CircuitState)
}

// NewCircuitBreaker creates a new circuit breaker
func NewCircuitBreaker(maxFailures int, timeout time.Duration, halfOpenMax int) *CircuitBreaker {
	return &CircuitBreaker{
		state:           StateClosed,
		maxFailures:     maxFailures,
		timeout:         timeout,
		halfOpenMaxReqs: halfOpenMax,
	}
}

// OnStateChange sets a callback for state transitions
func (cb *CircuitBreaker) OnStateChange(fn func(from, to CircuitState)) {
	cb.onStateChange = fn
}

// Allow checks if a request should be allowed through
func (cb *CircuitBreaker) Allow() bool {
	cb.mu.RLock()
	state := cb.state
	cb.mu.RUnlock()

	switch state {
	case StateClosed:
		return true
	case StateOpen:
		cb.mu.Lock()
		defer cb.mu.Unlock()
		// Check if timeout has elapsed — transition to half-open
		if time.Since(cb.lastFailure) > cb.timeout {
			cb.transition(StateHalfOpen)
			cb.successes = 0
			return true
		}
		return false
	case StateHalfOpen:
		cb.mu.RLock()
		defer cb.mu.RUnlock()
		return cb.successes < cb.halfOpenMaxReqs
	default:
		return true
	}
}

// RecordSuccess records a successful operation
func (cb *CircuitBreaker) RecordSuccess() {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	switch cb.state {
	case StateHalfOpen:
		cb.successes++
		if cb.successes >= cb.halfOpenMaxReqs {
			cb.transition(StateClosed)
			cb.failures = 0
			cb.successes = 0
		}
	case StateClosed:
		cb.failures = 0 // Reset on success
	}
}

// RecordFailure records a failed operation
func (cb *CircuitBreaker) RecordFailure() {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	cb.failures++
	cb.lastFailure = time.Now()

	switch cb.state {
	case StateClosed:
		if cb.failures >= cb.maxFailures {
			cb.transition(StateOpen)
		}
	case StateHalfOpen:
		cb.transition(StateOpen)
		cb.successes = 0
	}
}

// State returns the current circuit state
func (cb *CircuitBreaker) State() CircuitState {
	cb.mu.RLock()
	defer cb.mu.RUnlock()
	return cb.state
}

// transition performs a state change with optional callback
func (cb *CircuitBreaker) transition(to CircuitState) {
	from := cb.state
	cb.state = to
	if cb.onStateChange != nil {
		go cb.onStateChange(from, to)
	}
}

// String returns human-readable state name
func (s CircuitState) String() string {
	switch s {
	case StateClosed:
		return "CLOSED"
	case StateOpen:
		return "OPEN"
	case StateHalfOpen:
		return "HALF_OPEN"
	default:
		return "UNKNOWN"
	}
}
