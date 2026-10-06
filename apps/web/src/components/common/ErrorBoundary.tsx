import { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children?: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundaryClass extends Component<Props, State> {
  public state: State = {
    hasError: false
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-8">
          <div className="glass-card-elevated max-w-md w-full p-8 text-center border-red-500/30">
            <h2 className="text-xl font-semibold text-slate-100 mb-4 font-sans">Something went wrong</h2>
            <p className="text-slate-400 mb-8 font-sans text-sm">
              We encountered an unexpected error loading this view.
            </p>
            <button
              onClick={() => window.location.href = '/audit'}
              className="btn-primary w-full justify-center"
            >
              Return to Dashboard
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

// Wrapper to inject hooks if needed, though window.location.href is fine for a hard reset
export function ErrorBoundary({ children, fallback }: Props) {
  return (
    <ErrorBoundaryClass fallback={fallback}>
      {children}
    </ErrorBoundaryClass>
  );
}
