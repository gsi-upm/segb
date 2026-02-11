"""Application service around shared-context resolver."""

from __future__ import annotations

from dataclasses import dataclass

from ..utils.shared_context import (
    SharedContextReconcileResponse,
    SharedContextResolveRequest,
    SharedContextResolveResponse,
    SharedContextResolver,
)


@dataclass(slots=True)
class SharedContextService:
    resolver: SharedContextResolver

    def resolve(self, payload: SharedContextResolveRequest) -> SharedContextResolveResponse:
        """Resolves one local observation into a canonical shared context."""
        return self.resolver.resolve(payload)

    def reconcile(self) -> SharedContextReconcileResponse:
        """Runs reconciliation for ambiguous contexts."""
        return self.resolver.reconcile_pending()

    def stats(self) -> dict[str, int | str]:
        return self.resolver.stats()
