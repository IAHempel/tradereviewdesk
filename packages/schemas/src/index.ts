import { z } from "zod";

export const premarketBriefSchema = z.object({
  summary: z.string(),
  watchlist_priorities: z.array(
    z.object({
      symbol: z.string(),
      priority: z.enum(["high", "medium", "low"]),
      reason: z.string(),
    }),
  ),
  changes_to_watch: z.array(z.string()),
  focus_reminders: z.array(z.string()),
  session_checklist: z.array(z.string()),
  disclaimer: z.string(),
});

export const postCloseDebriefSchema = z.object({
  session_summary: z.string(),
  what_went_well: z.array(z.string()),
  deviations_from_plan: z.array(z.string()),
  risk_behavior_notes: z.array(z.string()),
  next_day_improvements: z.array(z.string()),
  disclaimer: z.string(),
});

export const weeklyReviewSchema = z.object({
  top_strengths: z.array(z.string()),
  repeated_mistakes: z.array(z.string()),
  setup_observations: z.array(z.string()),
  discipline_observations: z.array(z.string()),
  next_week_action_items: z.array(z.string()),
  disclaimer: z.string(),
});

export type PremarketBrief = z.infer<typeof premarketBriefSchema>;
export type PostCloseDebrief = z.infer<typeof postCloseDebriefSchema>;
export type WeeklyReview = z.infer<typeof weeklyReviewSchema>;
