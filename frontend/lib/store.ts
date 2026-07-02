"use client";

/**
 * Selection store (Zustand).
 *
 * State: a flat Set of selected talk IDs. Everything else (session totals,
 * conference totals, tri-state) is derived on read so it's always consistent.
 */

import { create } from "zustand";
import type { ConferenceDetail, Session, Talk } from "./api";

type SelectionStore = {
  // Core state
  selectedTalkIds: Set<string>;
  language: string;

  // Language
  setLanguage: (lang: string) => void;

  // Talk-level actions
  toggleTalk: (id: string) => void;
  isTalkSelected: (id: string) => boolean;

  // Session-level actions
  toggleSession: (session: Session) => void;
  sessionState: (session: Session) => "all" | "none" | "partial";

  // Conference-level actions
  selectAllConference: (detail: ConferenceDetail) => void;
  deselectAllConference: (detail: ConferenceDetail) => void;
  conferenceState: (detail: ConferenceDetail) => "all" | "none" | "partial";

  // Totals for the selection bar
  totalSelectedTalks: () => number;
  totalSelectedSessions: (sessions: Session[]) => number;

  // Build the API payload
  buildSelection: (details: ConferenceDetail[]) => {
    conference_id: string;
    talk_ids: string[];
  }[];

  clearAll: () => void;
};

export const useSelectionStore = create<SelectionStore>((set, get) => ({
  selectedTalkIds: new Set(),
  language: "eng",

  setLanguage: (lang) => set({ language: lang, selectedTalkIds: new Set() }),

  toggleTalk: (id) =>
    set((s) => {
      const next = new Set(s.selectedTalkIds);
      next.has(id) ? next.delete(id) : next.add(id);
      return { selectedTalkIds: next };
    }),

  isTalkSelected: (id) => get().selectedTalkIds.has(id),

  toggleSession: (session) => {
    const { selectedTalkIds, sessionState } = get();
    const state = sessionState(session);
    const next = new Set(selectedTalkIds);
    if (state === "all") {
      session.talks.forEach((t) => next.delete(t.id));
    } else {
      session.talks.forEach((t) => next.add(t.id));
    }
    set({ selectedTalkIds: next });
  },

  sessionState: (session) => {
    const { selectedTalkIds } = get();
    const count = session.talks.filter((t) => selectedTalkIds.has(t.id)).length;
    if (count === 0) return "none";
    if (count === session.talks.length) return "all";
    return "partial";
  },

  selectAllConference: (detail) =>
    set((s) => {
      const next = new Set(s.selectedTalkIds);
      detail.sessions.forEach((sess) => sess.talks.forEach((t) => next.add(t.id)));
      return { selectedTalkIds: next };
    }),

  deselectAllConference: (detail) =>
    set((s) => {
      const next = new Set(s.selectedTalkIds);
      detail.sessions.forEach((sess) => sess.talks.forEach((t) => next.delete(t.id)));
      return { selectedTalkIds: next };
    }),

  conferenceState: (detail) => {
    const allTalks = detail.sessions.flatMap((s) => s.talks) as Talk[];
    const { selectedTalkIds } = get();
    const count = allTalks.filter((t) => selectedTalkIds.has(t.id)).length;
    if (count === 0) return "none";
    if (count === allTalks.length) return "all";
    return "partial";
  },

  totalSelectedTalks: () => get().selectedTalkIds.size,

  totalSelectedSessions: (sessions) =>
    sessions.filter((s) => {
      const st = get().sessionState(s);
      return st === "all" || st === "partial";
    }).length,

  buildSelection: (details) =>
    details
      .map((d) => ({
        conference_id: d.id,
        talk_ids: d.sessions
          .flatMap((s) => s.talks)
          .filter((t) => get().selectedTalkIds.has(t.id))
          .map((t) => t.id),
      }))
      .filter((s) => s.talk_ids.length > 0),

  clearAll: () => set({ selectedTalkIds: new Set() }),
}));
