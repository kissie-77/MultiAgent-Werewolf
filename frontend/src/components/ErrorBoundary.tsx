import React from "react";

interface Props {
  children: React.ReactNode;
  /** Rendered instead of a white screen when a child throws. */
  fallback?: React.ReactNode;
  /** Optional label for the console error, to locate which boundary tripped. */
  label?: string;
}

interface State {
  hasError: boolean;
}

/**
 * Stops a single render-time exception from unmounting the whole React tree
 * (the human-vs-AI E2E found the seat game-over screen white-screening the
 * entire app on one undefined deref). Catches, logs, and shows `fallback`.
 */
export default class ErrorBoundary extends React.Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: unknown, info: unknown): void {
    // eslint-disable-next-line no-console
    console.error(`[ErrorBoundary${this.props.label ? ` ${this.props.label}` : ""}]`, error, info);
  }

  render(): React.ReactNode {
    if (this.state.hasError) {
      return this.props.fallback ?? null;
    }
    return this.props.children;
  }
}
