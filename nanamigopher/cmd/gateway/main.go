// Package main is the entry point for the NanamiGopher API Gateway.
// It initializes configuration, gRPC client, MCP manager, WebSocket hub,
// and starts the HTTP server with graceful shutdown support.
package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"nanamigopher/internal/api"
	"nanamigopher/internal/config"
	"nanamigopher/internal/observability"
)

func main() {
	// 1. Load configuration
	cfg, err := config.Load("")
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}

	// 2. Initialize observability
	obs := observability.NewConsoleObserver(cfg.App.Name)
	obs.Log("INFO", "Starting NanamiGopher Gateway")

	// 3. Initialize router (stubbed for Phase 1)
	router := api.NewRouter(cfg, obs)

	// 4. Start HTTP server
	addr := ":" + string(rune('8')+rune('0')) // placeholder
	_ = addr
	server := &http.Server{
		Addr:    ":8080",
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

	log.Fatal(server.ListenAndServe())
}
