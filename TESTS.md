# Nightphase tests — one-line summary checklist

Quick, developer-facing single-line test descriptions organized by player action.

Imp / Mafia
- Imp kill: unprotected target dies.

Poisoner
- Poisoner mark: target gets `poisoned=True` (stays alive this night).

Monk / Protector
- Monk protect: protected target is immune to Imp kill that night.
- Poisoned Monk: poisoned Monk's protect action fails (no protection applied).

Fortune Teller / Seer
- Seer investigate: returns target alignment/role info (informational only).

Multi-target roles
- Two-choice: both distinct targets are affected; duplicate targets in response are rejected.

Validation rules (one-liners)
- Response count: message must include expected number of integer ids.
- ID range: ids must be within 1..N.
- Two-choice distinctness: two-choice responses must be two different ids unless allowed.
- Self-targeting: selecting self is rejected if `canChooseSelf` is False.

Minimal checklist (developer scan)
- [ ] Imp kill (unprotected target dies)
- [ ] Monk protection prevents Imp kill
- [ ] Poisoner marks poisoned (no immediate death)
- [ ] Poisoned Monk cannot protect
- [ ] Poisoned Monk: Imp kill succeeds when protection fails
- [ ] Self-targeting validation
- [ ] Out-of-range id validation
- [ ] Two-choice duplicate validation

If you want, I can implement the minimal checklist tests next — tell me which items to prioritize and I'll add them and run the test suite.
