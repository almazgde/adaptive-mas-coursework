import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


RESULTS_DIR = Path("results")
REQUIRED_NODE_FIELDS = {"node_id", "start_time", "end_time", "duration"}


class TimelineTraceError(ValueError):
    """Raised when an execution trace cannot be plotted."""


def load_trace(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Trace file not found: {path}")
    with open(path, encoding="utf-8") as handle:
        trace = json.load(handle)
    validate_trace(trace)
    return trace


def validate_trace(trace: Dict[str, Any]) -> None:
    node_traces = trace.get("node_traces")
    if not isinstance(node_traces, list) or not node_traces:
        raise TimelineTraceError("Trace is empty or missing non-empty 'node_traces'.")

    missing_top_level = [field for field in ("topology_type", "duration") if field not in trace]
    if missing_top_level:
        raise TimelineTraceError(f"Trace is missing required field(s): {', '.join(missing_top_level)}")

    for index, node_trace in enumerate(node_traces):
        missing = REQUIRED_NODE_FIELDS - set(node_trace)
        if missing:
            fields = ", ".join(sorted(missing))
            raise TimelineTraceError(f"Node trace #{index} is missing required field(s): {fields}")


def plot_timeline(trace: Dict[str, Any], output_path: Path) -> Path:
    node_traces = sorted(
        trace["node_traces"],
        key=lambda item: (float(item["start_time"]), int(item.get("order", 0))),
    )
    trace_start = float(trace.get("start_time", min(float(item["start_time"]) for item in node_traces)))
    topology = trace.get("topology_type", "unknown")
    total_latency = float(trace.get("duration", 0.0))
    critical_path = trace.get("critical_path_duration")

    height = max(4.0, 0.42 * len(node_traces) + 1.8)
    fig, ax = plt.subplots(figsize=(12, height))
    colors = plt.get_cmap("tab10")

    for y_pos, node_trace in enumerate(node_traces):
        start = float(node_trace["start_time"]) - trace_start
        duration = float(node_trace.get("duration", float(node_trace["end_time"]) - float(node_trace["start_time"])))
        agent = node_trace.get("agent") or node_trace.get("result", {}).get("agent", "UnknownAgent")
        level = node_trace.get("level")
        label = node_trace["node_id"]
        if level is not None:
            label = f"{label} (L{level})"

        ax.barh(
            y_pos,
            duration,
            left=start,
            height=0.58,
            color=colors(y_pos % 10),
            edgecolor="#2f3437",
            linewidth=0.8,
            alpha=0.88,
        )
        ax.text(
            start + duration / 2,
            y_pos,
            agent,
            va="center",
            ha="center",
            fontsize=8,
            color="#111111",
        )
        ax.set_yticks(list(range(len(node_traces))))
        ax.set_yticklabels([_node_label(item) for item in node_traces])

    if critical_path is not None:
        ax.axvline(float(critical_path), color="#d62728", linestyle="--", linewidth=1.4, label="critical path")
        ax.legend(loc="lower right")

    subtitle = f"total latency: {total_latency:.3f}s"
    if critical_path is not None:
        subtitle += f" | critical path: {float(critical_path):.3f}s"
    ax.set_title(f"Execution timeline: {topology}\n{subtitle}")
    ax.set_xlabel("Time since trace start, seconds")
    ax.set_ylabel("Node")
    ax.grid(axis="x", linestyle=":", alpha=0.45)
    ax.invert_yaxis()
    fig.tight_layout()

    output_path.parent.mkdir(exist_ok=True)
    fig.savefig(output_path, dpi=160)
    plt.close(fig)
    return output_path


def output_path_for(trace_path: Path, trace: Dict[str, Any]) -> Path:
    topology = _safe_slug(str(trace.get("topology_type", "unknown")))
    stem = _safe_slug(trace_path.stem)
    return RESULTS_DIR / f"timeline_{stem}_{topology}.png"


def _node_label(node_trace: Dict[str, Any]) -> str:
    node_id = str(node_trace["node_id"])
    level = node_trace.get("level")
    if level is None:
        return node_id
    return f"{node_id} (L{level})"


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip())
    return slug.strip("_") or "trace"


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a Gantt-style timeline from an execution trace JSON.")
    parser.add_argument("trace_path", help="Path to execution_trace.json or scenario trace JSON.")
    parser.add_argument("--output", help="Optional PNG output path. Defaults to results/timeline_<trace>_<topology>.png.")
    args = parser.parse_args()

    try:
        trace_path = Path(args.trace_path)
        trace = load_trace(trace_path)
        output_path = Path(args.output) if args.output else output_path_for(trace_path, trace)
        saved_path = plot_timeline(trace, output_path)
    except (FileNotFoundError, json.JSONDecodeError, TimelineTraceError, KeyError, TypeError, ValueError) as exc:
        raise SystemExit(f"Cannot render execution timeline: {exc}") from exc

    print(f"Wrote execution timeline to {saved_path}")


if __name__ == "__main__":
    main()
