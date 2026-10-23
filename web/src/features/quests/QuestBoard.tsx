"use client";

import { useState } from "react";

const FILTERS = [
  { id: "all", label: "All quests" },
  { id: "in-progress", label: "In progress (0)" },
  { id: "done", label: "Done (0)" },
] as const;

type Filter = (typeof FILTERS)[number]["id"];

/** Filter tabs and quest sections. Every list is empty until quests are stored. */
export function QuestBoard() {
  const [filter, setFilter] = useState<Filter>("all");

  return (
    <div className="quest-board">
      <div className="quest-filters" role="group" aria-label="Filter quests">
        {FILTERS.map(({ id, label }) => (
          <button
            key={id}
            type="button"
            className="quest-filter"
            aria-pressed={filter === id}
            onClick={() => setFilter(id)}
          >
            {label}
          </button>
        ))}
      </div>

      {filter !== "done" && (
        <section className="quest-section" aria-labelledby="active-quests-heading">
          <div className="quest-section__heading-row">
            <h2 className="quest-section__heading" id="active-quests-heading">
              Keep exploring
            </h2>
            <span className="quest-section__detail">0 active quests</span>
          </div>
          <div className="quest-card quest-card--empty">
            <p className="quest-card__title">No quest in progress</p>
            <p className="quest-card__text">Start an adventure and your progress will show up here.</p>
          </div>
        </section>
      )}

      {filter === "all" && (
        <section className="quest-section" aria-labelledby="next-adventure-heading">
          <div className="quest-section__heading-row">
            <h2 className="quest-section__heading" id="next-adventure-heading">
              Your next adventure
            </h2>
            <span className="quest-section__detail">Near you</span>
          </div>
          <div className="quest-note">
            <p className="quest-note__title">No quests nearby yet.</p>
            <p className="quest-note__text">New adventures will appear here as local places are added.</p>
          </div>
        </section>
      )}

      {filter === "done" && (
        <section className="quest-section" aria-labelledby="done-quests-heading">
          <div className="quest-section__heading-row">
            <h2 className="quest-section__heading" id="done-quests-heading">
              Completed quests
            </h2>
            <span className="quest-section__detail">0 done</span>
          </div>
          <div className="quest-note">
            <p className="quest-note__title">No completed quests yet.</p>
            <p className="quest-note__text">Finish a quest to earn XP and see it here.</p>
          </div>
        </section>
      )}
    </div>
  );
}
