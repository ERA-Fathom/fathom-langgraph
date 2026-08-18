# fathom-langgraph

An external coherence check for a LangGraph graph's committed state.

It does not run your graph and it adds nothing to the runtime. It consumes the checkpoint lineage a graph
already produced (`graph.get_state_history(config)`) and reports one thing: whether the committed state is
internally consistent, that is, whether any committed record cites a key that the committed definition has
since renamed away. Think of it as an evaluator that sits next to LangSmith, not a second checkpointer.

## The branch it is built for

Two nodes writing a channel with no reducer in the same super-step raise `InvalidUpdateError`, and the step is
refused. That guard is clear and well understood.

On a reducer channel the two writes merge. That includes the case where one node built its write on the
pre-rename snapshot and cites a key the other node just renamed away. The super-step closes with no error, and
the committed state is left internally inconsistent. It is adjacent to silent-merge reports the maintainers
already triage; the difference here is reading the committed state for the contradiction instead of waiting for
a crash.

`example_fanout.py` reproduces exactly this, deterministically and with no model or API key:

```
pip install -r requirements.txt
python example_fanout.py
```

You get two runs. A sequential control, where the author node sees the rename and the read stays silent. And a
one-super-step fan-out, where the author node reads the pre-rename snapshot, the reducer merges both writes with
no error, and the read recovers the record that still cites the old key.

This is a stressed reproduction. The concurrent branch is forced to expose the merge contract; it is not a claim
that a LangGraph graph does this on its own.

## Scope, and what this is not

This repository is the read only. The decomposition of a coherence break into task difficulty versus the cost
of keeping the graph's own record consistent, and scoring across models and runtimes, is the Fathom program at
[Embedded Risk Analytics](https://embeddedriskanalytics.com) and is not included here.

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE). Fathom(TM) is a trademark of Embedded Risk Analytics.
