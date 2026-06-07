import { describe, it, expect } from "vitest";
import {
  lineupSummary,
  standardLineupForCount,
  validateCustomLineup,
  effectivePlayableRoles,
  roleOptionLabel,
  FALLBACK_PLAYABLE_ROLES,
} from "./roleCatalog";

describe("roleCatalog", () => {
  it("builds standard 6p lineup", () => {
    const lineup = standardLineupForCount(6);
    expect(lineup).toHaveLength(6);
    expect(lineup.filter((r) => r === "Werewolf")).toHaveLength(2);
  });

  it("summarizes duplicate roles", () => {
    expect(lineupSummary(["Werewolf", "Werewolf", "Seer"], [])).toContain("狼人×2");
  });

  it("uses fallback roles when API list empty", () => {
    expect(effectivePlayableRoles([])).toHaveLength(FALLBACK_PLAYABLE_ROLES.length);
    expect(roleOptionLabel(FALLBACK_PLAYABLE_ROLES[0])).toContain("狼人");
  });

  it("rejects lineup without wolves", () => {
    expect(
      validateCustomLineup(
        ["Seer", "Villager", "Villager", "Villager", "Villager", "Villager"],
        [],
      ),
    ).toBeTruthy();
  });
});
