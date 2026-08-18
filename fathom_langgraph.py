"""
fathom_langgraph.py - an external coherence read for a LangGraph graph's committed state.

It does not run, and it adds nothing to the runtime. It consumes the checkpoint lineage a graph already
produced (the list of StateSnapshots from `graph.get_state_history(config)`) and reports whether the
committed state is internally consistent: whether any committed record cites a key that the committed
definition has since renamed away.

This is the read only. The decomposition of a coherence break into task difficulty vs the cost of keeping
the graph's own record consistent, and scoring across models, is the Fathom program and is not in this repo.
"""
from typing import Any, Dict, List


def read(snapshots: List[Any]) -> Dict[str, Any]:
    """snapshots: the value of list(graph.get_state_history(config)), newest first.
    Returns a coherence verdict over the committed (latest) state."""
    if not snapshots:
        return {"coherent": True, "findings": [], "note": "no checkpoints"}
    committed = snapshots[0].values
    definition = committed.get("definition")
    records = committed.get("records", []) or []
    findings = []
    for i, r in enumerate(records):
        cited = r.get("cites") if isinstance(r, dict) else None
        if cited is not None and definition is not None and cited != definition:
            findings.append({
                "record_index": i,
                "record_cites": cited,
                "committed_definition": definition,
                "issue": "authored-contradiction: a committed record cites a key the committed "
                         "definition renamed away",
            })
    return {
        "coherent": len(findings) == 0,
        "findings": findings,
        "committed_definition": definition,
        "records_examined": len(records),
        "checkpoints_in_lineage": len(snapshots),
    }
