// Package main is the entry point for the MaigoKite API Gateway.
// It initializes configuration and the gRPC client to Agent Core,
// and starts the HTTP server with graceful shutdown support.
package main

import (
	"context"
	"io"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"syscall"
	"time"

	"maigokite/gateway/internal/api"
	"maigokite/gateway/internal/config"
	agentgrpc "maigokite/gateway/internal/grpc"
	"maigokite/gateway/internal/observability"
)

func main() {
	lifecycle, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()
	if os.Getenv("MAIGOKITE_PARENT_PIPE") == "1" {
		go func() {
			// Only a managed launcher supplies this pipe. Its disappearance
			// must end this Gateway too, including during Core connection.
			_, _ = io.Copy(io.Discard, os.Stdin)
			stop()
		}()
	}
	// 1. Load configuration
	cfg, err := config.Load(os.Getenv("MAIGOKITE_CONFIG"))
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}

	// 2. Initialize observability
	obs := observability.NewConsoleObserver(cfg.App.Name)
	obs.Log("INFO", "Starting MaigoKite Gateway")

	// 3. Connect to the Python-owned Agent Core.
	dialCtx, dialCancel := context.WithTimeout(lifecycle, time.Duration(cfg.GRPC.Timeout)*time.Second)
	client, err := agentgrpc.DialAgentClient(dialCtx, "127.0.0.1:"+strconv.Itoa(cfg.GRPC.Port))
	dialCancel()
	if err != nil {
		if lifecycle.Err() != nil {
			return
		}
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
	shutdownDone := make(chan struct{})
	go func() {
		defer close(shutdownDone)
		<-lifecycle.Done()
		obs.Log("INFO", "Shutting down...")
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		server.Shutdown(ctx)
	}()

	if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatal(err)
	}
	// ListenAndServe returns as soon as shutdown starts, not when requests drain.
	<-shutdownDone
}
