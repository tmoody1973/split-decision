// Persona registry — accents from assets/sprites/THEME.md. The renderer hard-fails on
// any agent id outside this table (contract §4). "foreperson" is a moderator, not a
// juror, but appears as a speaker so it carries a colour and label too.

export interface Persona {
  id: string;
  display: string;
  // Compact bench label — the full display names overlap at 9-across.
  short: string;
  accent: string;
}

export const JURIST_ORDER = [
  "textualist",
  "originalist",
  "living_constitutionalist",
  "pragmatist",
  "precedent_maximalist",
  "federalism_hawk",
  "civil_libertarian",
  "process_formalist",
  "minimalist",
] as const;

export const PERSONAS: Record<string, Persona> = {
  textualist: { id: "textualist", display: "The Textualist", short: "Textualist", accent: "#7a1f2b" },
  originalist: { id: "originalist", display: "The Originalist", short: "Originalist", accent: "#5b4a2f" },
  living_constitutionalist: {
    id: "living_constitutionalist",
    display: "The Living Constitutionalist",
    short: "Living",
    accent: "#2e6f5e",
  },
  pragmatist: { id: "pragmatist", display: "The Pragmatist", short: "Pragmatist", accent: "#c27b2c" },
  precedent_maximalist: {
    id: "precedent_maximalist",
    display: "The Precedent Maximalist",
    short: "Precedent",
    accent: "#4a4e69",
  },
  federalism_hawk: { id: "federalism_hawk", display: "The Federalism Hawk", short: "Federalism", accent: "#8c3b00" },
  civil_libertarian: { id: "civil_libertarian", display: "The Civil Libertarian", short: "Liberties", accent: "#2b6cb0" },
  process_formalist: { id: "process_formalist", display: "The Process Formalist", short: "Process", accent: "#6b7280" },
  minimalist: { id: "minimalist", display: "The Minimalist", short: "Minimalist", accent: "#9b8ec4" },
  foreperson: { id: "foreperson", display: "The Foreperson", short: "Foreperson", accent: "#1f2a44" },
};

export function personaFor(agent: string): Persona {
  const p = PERSONAS[agent];
  if (!p) {
    throw new Error(`Unknown agent "${agent}" — not in the persona registry`);
  }
  return p;
}
