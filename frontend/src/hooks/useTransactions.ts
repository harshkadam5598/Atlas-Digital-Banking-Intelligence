import { getTransactions } from "../api/hubs/operations";
import { useApiResource } from "./useApiResource";

/** GET /api/v1/operations/transactions, fetched once on mount. */
export function useTransactions() {
  return useApiResource(() => getTransactions());
}
