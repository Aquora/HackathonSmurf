"use client";

import { useActionState, useId } from "react";
import { generateQuest, type NewQuestState } from "./actions";

const EXAMPLES = ["2 hours and $25. Coffee and art", "Cheap food spots, 90 minutes", "Somewhere new, any budget"];

/** Free-text quest request. Time, budget and interests are read by the planner; blanks use its defaults. */
export function NewQuestForm() {
  const [state, formAction, pending] = useActionState<NewQuestState, FormData>(generateQuest, {});
  const inputId = useId();
  const hintId = useId();

  return (
    <form action={formAction} className="new-quest" aria-busy={pending}>
      <label className="new-quest__label" htmlFor={inputId}>
        What are you in the mood for?
      </label>
      <textarea
        id={inputId}
        className="new-quest__input"
        name="message"
        rows={3}
        maxLength={2000}
        required
        disabled={pending}
        defaultValue={state.message}
        key={state.message ?? ""}
        placeholder={EXAMPLES[0]}
        aria-describedby={hintId}
      />
      <p className="new-quest__hint" id={hintId}>
        Mention time, budget and interests. Anything you leave out uses 90 minutes, $30 and no
        preference. Every quest is a driving route that starts and ends at Cal Poly Pomona.
      </p>
      <button type="submit" className="new-quest__submit" disabled={pending}>
        {pending ? "Planning your quest…" : "Plan my quest"}
      </button>
      {pending && (
        <p className="new-quest__status" role="status">
          Finding open places and planning a route. This can take up to 30 seconds.
        </p>
      )}

      {state.error && !pending && (
        <div className="new-quest__error" role="alert">
          <p>{state.error}</p>
          {state.preferences && (
            <p className="new-quest__understood">
              We understood: {state.preferences.desiredTime} min, ${state.preferences.desiredBudget},{" "}
              {state.preferences.locationPreference}, by {state.preferences.travelMethod}. Try more time or a bigger budget.
            </p>
          )}
          {state.requestId && <p className="new-quest__request-id">Reference: {state.requestId}</p>}
        </div>
      )}
    </form>
  );
}
