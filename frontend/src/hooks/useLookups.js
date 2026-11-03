import { useQuery } from "@tanstack/react-query";

import { getLookups } from "../api/lookups";

export function useLookups() {
  return useQuery({
    queryKey: ["lookups"],
    queryFn: getLookups,
    staleTime: Infinity,
  });
}
