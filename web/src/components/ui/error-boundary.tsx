"use client";

import React from "react";
import { Button } from "@/components/ui/button";

interface ErrorBoundaryProps {
  fallback?: React.ReactNode;
  onError?: (error: Error, info: React.ErrorInfo) => void;
  children: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends React.Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo): void {
    this.props.onError?.(error, info);
  }

  handleRetry = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): React.ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex flex-col items-center justify-center gap-3 rounded-xl border bg-card p-6 text-center">
          <p className="text-sm text-muted-foreground">
            Une erreur est survenue.
          </p>
          <Button variant="outline" size="sm" onClick={this.handleRetry}>
            Réessayer
          </Button>
        </div>
      );
    }

    return this.props.children;
  }
}
