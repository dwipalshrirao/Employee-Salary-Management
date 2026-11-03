import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";

export function useUrlState(defaults) {
  const [searchParams, setSearchParams] = useSearchParams();

  const values = useMemo(() => {
    const next = { ...defaults };
    for (const key of Object.keys(defaults)) {
      const value = searchParams.get(key);
      if (value !== null) {
        next[key] = value;
      }
    }
    return next;
  }, [defaults, searchParams]);

  const update = useCallback(
    (changes) => {
      setSearchParams(
        (current) => {
          const next = new URLSearchParams(current);
          for (const [key, value] of Object.entries(changes)) {
            if (
              value === undefined ||
              value === null ||
              value === "" ||
              String(value) === String(defaults[key])
            ) {
              next.delete(key);
            } else {
              next.set(key, String(value));
            }
          }
          return next;
        },
        { replace: true },
      );
    },
    [defaults, setSearchParams],
  );

  const reset = useCallback(() => {
    setSearchParams(new URLSearchParams(), { replace: true });
  }, [setSearchParams]);

  return { values, update, reset };
}
