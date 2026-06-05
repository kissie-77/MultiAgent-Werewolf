import { useEffect, useState } from "react";

interface PageState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

export function usePageData<T>(loader: () => Promise<T>, deps: unknown[] = []) {
  const [state, setState] = useState<PageState<T>>({
    data: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;
    setState((prev) => ({ ...prev, loading: true, error: null }));
    loader()
      .then((data) => {
        if (!cancelled) setState({ data, loading: false, error: null });
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setState({
            data: null,
            loading: false,
            error: err instanceof Error ? err.message : "加载失败",
          });
        }
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return state;
}
