# NanamiGopher Gateway Build

GOCMD=go
GOBUILD=$(GOCMD) build
GORUN=$(GOCMD) run
GOMOD=$(GOCMD) mod

BINARY_NAME=gateway
CMD_PATH=./cmd/gateway

.PHONY: all build run clean tidy proto test

all: build

# Build the gateway binary
build:
	$(GOBUILD) -o $(BINARY_NAME) $(CMD_PATH)

# Run the gateway in development mode
run:
	$(GORUN) $(CMD_PATH)

# Clean build artifacts
clean:
	rm -f $(BINARY_NAME)
	rm -f go.sum

# Tidy dependencies
tidy:
	$(GOMOD) tidy

# Generate Go code from proto files
proto:
	protoc --go_out=. --go-grpc_out=. \
		--proto_path=./internal/grpc/pb \
		./internal/grpc/pb/agent.proto

# Run tests
test:
	$(GOCMD) test ./...

# Format code
fmt:
	$(GOCMD) fmt ./...
