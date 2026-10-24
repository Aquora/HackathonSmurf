"use client";

import Link from "next/link";
import { useState } from "react";
import { NewQuestForm } from "./NewQuestForm";

/** Board-card data (plain values only; built on the server from saved quests). */
export interface QuestSummary {
  id: string;
  request: string;
  stopNames: string[];
  stopsDone: number;
  estimatedCost: number;
  totalTime: number | null;
  mock: boolean;
  started: boolean;
  done: boolean;
}

type Filter = "all" | "in-progress" | "done";

function QuestCard({ quest }: { quest: QuestSummary }) {
  const total = quest.stopNames.length;
  const progress = quest.done
    ? "Completed"
    : !quest.started
      ? "Not started"
      : quest.stopsDone === total
        ? "Ready to finish"
        : `${quest.stopsDone} of ${total} stops`;
  return (
    <Link className="quest-card quest-card--link" href={`/quests/${quest.id}`}>
      <span className="quest-card__top">
        <span className="quest-card__title">{quest.stopNames.join(" → ")}</span>
        {quest.mock && <span className="demo-badge">Demo</span>}
      </span>
      <span className="quest-card__text">“{quest.request}”</span>
      <span className="quest-card__meta">
        {progress} · est. ${quest.estimatedCost.toFixed(2)}
        {quest.totalTime ? ` · ~${quest.totalTime} min` : ""}
      </span>
      <span className="quest-card__bar" aria-hidden="true">
        <span className="quest-card__fill" style={{ width: `${Math.round((quest.stopsDone / total) * 100)}%` }} />
      </span>
    </Link>
  );
}

/** Filter tabs, the new-quest form, and the player's saved quests. */
export function QuestBoard({ active, done }: { active: QuestSummary[]; done: QuestSummary[] }) {
  const [filter, setFilter] = useState<Filter>("all");
  const filters: { id: Filter; label: string }[] = [
    { id: "all", label: "All quests" },
    { id: "in-progress", label: `In progress (${active.length})` },
    { id: "done", label: `Done (${done.length})` },
  ];

  return (
    <div className="quest-board">
      <div className="quest-filters" role="group" aria-label="Filter quests">
        {filters.map(({ id, label }) => (
          <button key={id} type="button" className="quest-filter" aria-pressed={filter === id} onClick={() => setFilter(id)}>
            {label}
          </button>
        ))}
      </div>

      {filter === "all" && (
        <section className="quest-section" aria-labelledby="next-adventure-heading">
          <div className="quest-section__heading-row">
            <h2 className="quest-section__heading" id="next-adventure-heading">
              Your next adventure
            </h2>
            <span className="quest-section__detail">Near campus</span>
          </div>
          <NewQuestForm />
        </section>
      )}

      {filter !== "done" && (
        <section className="quest-section" aria-labelledby="active-quests-heading">
          <div className="quest-section__heading-row">
            <h2 className="quest-section__heading" id="active-quests-heading">
              Keep exploring
            </h2>
            <span className="quest-section__detail">
              {active.length} active {active.length === 1 ? "quest" : "quests"}
            </span>
          </div>
          {active.length === 0 ? (
            <div className="quest-card quest-card--empty">
              <p className="quest-card__title">No quest in progress</p>
              <p className="quest-card__text">Plan an adventure and your progress will show up here.</p>
            </div>
          ) : (
            active.map((quest) => <QuestCard key={quest.id} quest={quest} />)
          )}
        </section>
      )}

      {filter !== "in-progress" && (
        <section className="quest-section" aria-labelledby="done-quests-heading">
          <div className="quest-section__heading-row">
            <h2 className="quest-section__heading" id="done-quests-heading">
              Completed quests
            </h2>
            <span className="quest-section__detail">{done.length} done</span>
          </div>
          {done.length === 0 ? (
            <div className="quest-note">
              <p className="quest-note__title">No completed quests yet.</p>
              <p className="quest-note__text">Finish a quest to earn XP and see it here.</p>
            </div>
          ) : (
            done.map((quest) => <QuestCard key={quest.id} quest={quest} />)
          )}
        </section>
      )}
    </div>
  );
}
