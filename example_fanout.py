"""
example_fanout.py - a minimal, deterministic (NO model, NO API key) reproduction of the fan-out branch the
read is built for, plus a coherent control it stays silent on.

Setup: a graph holds a `definition` (the canonical key name) and a reducer channel `records` (list, merged by
concatenation). A rename node changes `definition` from "guest_id" to "customer_id" and writes a record that
cites the new key. An author node writes a record that cites whatever key it can see.

  * COHERENT control (sequential): author runs AFTER rename, sees "customer_id", cites it. Read stays silent.
  * FAN-OUT break (one super-step): author runs CONCURRENTLY with rename, so it reads the pre-rename snapshot
    ("guest_id") and cites the old key. Both writes merge through the reducer with no error. The committed
    state ends internally inconsistent: definition == "customer_id" while a committed record cites "guest_id".
    The read recovers exactly that record from get_state_history.

Note: this is a stressed reproduction. The concurrent branch is forced to expose the merge contract; it is not
a claim that a LangGraph graph does this on its own.
"""
import operator
from typing import Annotated, List, TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from fathom_langgraph import read

OLD, NEW = "guest_id", "customer_id"


class S(TypedDict):
    definition: str
    records: Annotated[List[dict], operator.add]


def rename_node(state: S):
    # renames the canonical key and records a citation to the NEW key
    return {"definition": NEW, "records": [{"by": "rename", "cites": NEW}]}


def author_node(state: S):
    # cites whatever the node can currently see. In the concurrent super-step it sees the pre-rename snapshot.
    return {"records": [{"by": "author", "cites": state["definition"]}]}


def build(concurrent: bool):
    g = StateGraph(S)
    g.add_node("rename", rename_node)
    g.add_node("author", author_node)
    if concurrent:
        g.add_edge(START, "rename")   # both fan out from START -> one super-step
        g.add_edge(START, "author")
        g.add_edge("rename", END)
        g.add_edge("author", END)
    else:
        g.add_edge(START, "rename")   # sequential -> author sees the rename
        g.add_edge("rename", "author")
        g.add_edge("author", END)
    return g.compile(checkpointer=MemorySaver())


def run(concurrent: bool, thread: str):
    graph = build(concurrent)
    cfg = {"configurable": {"thread_id": thread}}
    graph.invoke({"definition": OLD, "records": []}, cfg)
    snapshots = list(graph.get_state_history(cfg))
    return read(snapshots)


if __name__ == "__main__":
    coherent = run(concurrent=False, thread="coherent")
    broken = run(concurrent=True, thread="fanout")
    import json
    print("COHERENT control (sequential):")
    print(json.dumps(coherent, indent=2))
    print("\nFAN-OUT break (one super-step):")
    print(json.dumps(broken, indent=2))
    ok = coherent["coherent"] is True and broken["coherent"] is False and \
        any(f["record_cites"] == OLD for f in broken["findings"])
    print("\nSELFTEST:", "PASS" if ok else "FAIL")
