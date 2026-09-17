// Package main is the entry point for the NanamiGopher API Gateway.
// It initializes configuration and the gRPC client to Agent Core,
// and starts the HTTP server with graceful shutdown support.
package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"syscall"
	"time"

	"github.com/nanamigopher/nanamigopher/gateway/internal/api"
	"github.com/nanamigopher/nanamigopher/gateway/internal/config"
	agentgrpc "github.com/nanamigopher/nanamigopher/gateway/internal/grpc"
	"github.com/nanamigopher/nanamigopher/gateway/internal/observability"
)

func main() {
	// 1. Load configuration
	cfg, err := config.Load(os.Getenv("NANAMI_CONFIG"))
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}

	// 2. Initialize observability
	obs := observability.NewConsoleObserver(cfg.App.Name)
	obs.Log("INFO", "Starting NanamiGopher Gateway")

	// 3. Connect to the Python-owned Agent Core.
	dialCtx, dialCancel := context.WithTimeout(context.Background(), time.Duration(cfg.GRPC.Timeout)*time.Second)
	client, err := agentgrpc.DialAgentClient(dialCtx, "127.0.0.1:"+strconv.Itoa(cfg.GRPC.Port))
	dialCancel()
	if err != nil {
		log.Fatalf("connect Agent Core: %v", err)
	}
	defer client.Close()
	router := api.NewRouter(cfg, obs, client)

	// 4. Start HTTP server
	server := &http.Server{
		Addr:    "127.0.0.1:" + strconv.Itoa(cfg.HTTP.Port),
		Handler: router,
	}

	// 5. Graceful shutdown
	go func() {
		sigCh := make(chan os.Signal, 1)
		signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
		<-sigCh
		obs.Log("INFO", "Shutting down...")
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		server.Shutdown(ctx)
	}()

	if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatal(err)
	}
}
