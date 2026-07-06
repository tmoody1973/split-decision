import { personaFor } from "./personas";
import type { NormalizedEvent, Position } from "./types";

// "The Record" — the court-reporter transcript. It is the visible proof of the tape-
// integrity rule: what scrolls here is events.jsonl rendered, nothing paraphrased. Lines
// append as their events cross the playhead; on seek the panel is rebuilt from state.
// Clicking any line seeks to that event. Auto-scroll pauses while the pointer is over it.
export class RecordPanel {
  private readonly head: HTMLElement;
  private readonly scroll: HTMLElement;
  private readonly tallyEl: HTMLElement;
  private hovering = false;

  constructor(
    root: HTMLElement,
    private readonly onSeek: (ms: number) => void,
  ) {
    root.innerHTML = "";
    this.head = document.createElement("div");
    this.head.className = "record-head";
    this.head.innerHTML =
      '<div class="record-title">The Record</div><div class="tally"></div>';
    this.tallyEl = this.head.querySelector(".tally") as HTMLElement;
    this.scroll = document.createElement("div");
    this.scroll.className = "record-scroll";
    root.append(this.head, this.scroll);

    this.scroll.addEventListener("pointerenter", () => (this.hovering = true));
    this.scroll.addEventListener("pointerleave", () => (this.hovering = false));
    this.setTally(0, 0);
  }

  clear(): void {
    this.scroll.innerHTML = "";
  }

  /** Rebuild the panel to reflect exactly the events at or before t (used on seek). */
  rebuild(events: NormalizedEvent[], t: number): void {
    this.clear();
    for (const ev of events) {
      if (ev.t <= t) this.append(ev);
    }
    this.scroll.scrollTop = this.scroll.scrollHeight;
  }

  setTally(affirm: number, reverse: number): void {
    this.tallyEl.innerHTML = `<span class="aff">AFFIRM ${affirm}</span><span class="rev">REVERSE ${reverse}</span>`;
  }

  append(ev: NormalizedEvent): void {
    const line = this.render(ev);
    if (!line) return;
    line.dataset.t = String(ev.t);
    line.addEventListener("click", () => this.onSeek(ev.t));
    this.scroll.appendChild(line);
    if (!this.hovering) this.scroll.scrollTop = this.scroll.scrollHeight;
  }

  private render(ev: NormalizedEvent): HTMLElement | null {
    switch (ev.type) {
      case "speak": {
        const p = personaFor(ev.agent);
        const el = document.createElement("div");
        el.className = "line speak";
        el.innerHTML = `<span class="ts">${fmt(ev.t)}</span><span class="who" style="color:${p.accent}">${p.display}:</span> ${escapeHtml(ev.text)}${warn(ev.synthesized, "synthesized")}`;
        return el;
      }
      case "studio": {
        const p = personaFor(ev.agent);
        const el = document.createElement("div");
        el.className = "line studio";
        el.innerHTML = `<span class="ts">${fmt(ev.t)}</span><span class="who" style="color:${p.accent}">STUDIO · ${p.display}:</span> ${escapeHtml(ev.text)}`;
        return el;
      }
      case "foreperson": {
        const el = document.createElement("div");
        el.className = "line foreperson";
        el.innerHTML = `<span class="ts">${fmt(ev.t)}</span>FOREPERSON — ${escapeHtml(ev.text)}`;
        return el;
      }
      case "vote_change": {
        const p = personaFor(ev.agent);
        const el = document.createElement("div");
        el.className = "line system";
        el.textContent = `⚖ ${p.display.toUpperCase()} changes vote: ${ev.from.toUpperCase()} → ${ev.to.toUpperCase()} (rd ${ev.round})${warn(ev.influence_inferred, "influence inferred")}${warn(ev.reason_inferred, "reason inferred")}`;
        return el;
      }
      case "verdict": {
        const el = document.createElement("div");
        el.className = "line verdict";
        el.textContent = `VERDICT — ${ev.position.toUpperCase()} ${ev.vote_split}`;
        return el;
      }
      case "reveal": {
        const el = document.createElement("div");
        el.className = "line verdict";
        el.textContent = `THE REAL COURT — ${ev.actual.toUpperCase()} ${ev.actual_split} · panel ${ev.match ? "MATCHED" : "MISSED"}`;
        return el;
      }
      default:
        return null; // session_start, vote (private), move — not part of the record
    }
  }
}

export function tallyOf(votes: Record<string, Position | "unknown">): { affirm: number; reverse: number } {
  let affirm = 0;
  let reverse = 0;
  for (const v of Object.values(votes)) {
    if (v === "affirm") affirm += 1;
    else if (v === "reverse") reverse += 1;
  }
  return { affirm, reverse };
}

/** Degraded-data marker suffix — mirrors the engine's marked-never-silent flags. */
function warn(flag: boolean | undefined, label: string): string {
  return flag ? ` · ⚠ ${label}` : "";
}

function fmt(ms: number): string {
  const s = Math.floor(ms / 1000);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) => {
    switch (c) {
      case "&":
        return "&amp;";
      case "<":
        return "&lt;";
      case ">":
        return "&gt;";
      case '"':
        return "&quot;";
      default:
        return "&#39;";
    }
  });
}
