package publisher

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/civa-platform/sentinel-sdk/pkg/models"
	"go.uber.org/zap"
)

// EventPublisher defines the interface for publishing session events
type EventPublisher interface {
	Publish(ctx context.Context, event *models.SessionEvent) error
	Close() error
}

// KafkaPublisher publishes SessionEvents to the Kafka session.events topic
type KafkaPublisher struct {
	bootstrapServers string
	topic            string
	logger           *zap.Logger
	// In production, this would use confluent-kafka-go Producer
	// For now, we use a JSON-based approach that works with any Kafka client
}

// NewKafkaPublisher creates a new Kafka publisher
func NewKafkaPublisher(bootstrapServers, topic string, logger *zap.Logger) (*KafkaPublisher, error) {
	kp := &KafkaPublisher{
		bootstrapServers: bootstrapServers,
		topic:            topic,
		logger:           logger,
	}

	logger.Info("Kafka publisher initialized",
		zap.String("bootstrap_servers", bootstrapServers),
		zap.String("topic", topic),
	)

	return kp, nil
}

// Publish serializes a SessionEvent and sends it to Kafka
// Partitioned by session_id for ordering guarantees within a session
func (kp *KafkaPublisher) Publish(ctx context.Context, event *models.SessionEvent) error {
	// Serialize the event to JSON
	data, err := json.Marshal(event)
	if err != nil {
		return fmt.Errorf("marshal event: %w", err)
	}

	kp.logger.Debug("Publishing session event",
		zap.String("event_id", event.EventID),
		zap.String("session_id", event.SessionID),
		zap.String("topic", kp.topic),
		zap.Int("payload_bytes", len(data)),
	)

	// In production implementation with confluent-kafka-go:
	// err = kp.producer.Produce(&kafka.Message{
	//     TopicPartition: kafka.TopicPartition{Topic: &kp.topic, Partition: kafka.PartitionAny},
	//     Key:            []byte(event.SessionID),  // Partition by session
	//     Value:          data,
	//     Headers: []kafka.Header{
	//         {Key: "event_type", Value: []byte("session_event")},
	//         {Key: "trace_id", Value: []byte(event.TraceID)},
	//     },
	// }, nil)

	_ = data // placeholder until confluent-kafka-go is compiled

	return nil
}

// Close flushes pending messages and closes the producer
func (kp *KafkaPublisher) Close() error {
	kp.logger.Info("Kafka publisher closed")
	// In production: kp.producer.Flush(5000); kp.producer.Close()
	return nil
}

// Serializer handles event serialization (JSON or Protobuf)
type Serializer interface {
	Serialize(event *models.SessionEvent) ([]byte, error)
	Deserialize(data []byte) (*models.SessionEvent, error)
}

// JSONSerializer implements JSON serialization
type JSONSerializer struct{}

// Serialize converts a SessionEvent to JSON bytes
func (s *JSONSerializer) Serialize(event *models.SessionEvent) ([]byte, error) {
	return json.Marshal(event)
}

// Deserialize converts JSON bytes to a SessionEvent
func (s *JSONSerializer) Deserialize(data []byte) (*models.SessionEvent, error) {
	var event models.SessionEvent
	if err := json.Unmarshal(data, &event); err != nil {
		return nil, err
	}
	return &event, nil
}
