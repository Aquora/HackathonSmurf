"use client";

import { motion } from "motion/react";

// Shared Figma timeline for the "Quest" letters and the typing cursor.
const LOOP_SECONDS = 4.8;
const LETTER_START_MS = 150;
const LETTER_STEP_MS = 130;

const QUEST_LETTERS = ["Q", "u", "e", "s", "t"];

function letterFadeIn(index: number) {
  const start = (LETTER_START_MS + index * LETTER_STEP_MS) / (LOOP_SECONDS * 1000);
  const end = start + LETTER_STEP_MS / (LOOP_SECONDS * 1000);
  return {
    animate: { opacity: [0, 0, 1, 1] },
    transition: {
      opacity: { duration: LOOP_SECONDS, times: [0, start, end, 1], ease: "linear" as const, repeat: Infinity },
    },
  };
}

/**
 * "Local Quest" wordmark with the letter-by-letter typing animation from Figma.
 * Markup is identical on server and client; prefers-reduced-motion is handled in
 * LandingPage.css, which pins the letters and cursor in their final state.
 */
export function HeroTitle() {
  return (
    <h1 className="hero-title" aria-label="Local Quest">
      <span className="hero-title__local" aria-hidden="true">
        Local
      </span>
      <span className="hero-title__quest" aria-hidden="true">
        {QUEST_LETTERS.map((letter, index) => (
          <motion.span key={index} initial={{ opacity: 0 }} {...letterFadeIn(index)}>
            {letter}
          </motion.span>
        ))}
      </span>
      <motion.span
        className="hero-title__cursor"
        aria-hidden="true"
        initial={{ opacity: 1, x: -232 }}
        animate={{
          opacity: [1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1],
          x: [-232, -232, -184, -184, -136, -136, -88, -88, -40, -40, 0, 0],
        }}
        transition={{
          opacity: {
            duration: 4.8,
            times: [0, 0.229, 0.2292, 0.3019, 0.3021, 0.3748, 0.375, 0.4477, 0.4479, 0.6248, 0.625, 0.6977, 0.6979, 0.7706, 0.7708, 0.8435, 0.8438, 0.9165, 0.9167, 0.9894, 0.9896, 1],
            ease: "linear",
            repeat: Infinity,
          },
          x: {
            duration: 4.8,
            times: [0, 0.031, 0.0313, 0.0649, 0.0651, 0.0988, 0.099, 0.1326, 0.1328, 0.1665, 0.1667, 1],
            ease: "linear",
            repeat: Infinity,
          },
        }}
      />
    </h1>
  );
}
