-- SPDX-License-Identifier: Apache-2.0
-- Local wrapper for ART-006 revision ede0151a35c86b6395cf67dd034811d22a92c7ba.

import Erdos848.PaperGeneratedCertificateProvider
import Erdos848.HallReduction
import Erdos848.SharpnessCore

namespace Erdos848Completion

/-!
This is the literal positive-integer theorem requested by the source problem.
It deliberately expands `OriginalProblem848Statement` so that interval,
diagonal, predicate, and benchmark drift are visible at the final interface.
-/

theorem erdos848_all_positive :
    ∀ N : ℕ, 1 ≤ N →
      ∀ A : Finset ℕ,
        A ⊆ Finset.Icc 1 N →
        (∀ a ∈ A, ∀ b ∈ A, ¬ Squarefree (a * b + 1)) →
        A.card ≤
          ((Finset.Icc 1 N).filter fun n => n % 25 = 7).card := by
  intro N _hN A hA hproduct
  exact Erdos848.PaperGeneratedCertificateProvider.all_N N A hA hproduct

/-! The residue-seven construction witnesses sharpness of the upper bound. -/

theorem residue_seven_witness (N : ℕ) :
    Erdos848.OriginalA7 N ⊆ Finset.Icc 1 N ∧
      Erdos848.NonSquarefreeProductProp (Erdos848.OriginalA7 N) := by
  constructor
  · intro n hn
    exact (Finset.mem_filter.mp hn).1
  · exact Erdos848.originalA7_has_property N

/-!
The residue-eighteen class is another admissible construction.  Its exact
cardinality is stated separately, so the formal interface makes no false
uniqueness assertion when that cardinality ties the residue-seven class.
-/

theorem residue_eighteen_witness (N : ℕ) :
    Erdos848.OriginalA18 N ⊆ Finset.Icc 1 N ∧
      Erdos848.NonSquarefreeProductProp (Erdos848.OriginalA18 N) := by
  constructor
  · intro n hn
    exact (Finset.mem_filter.mp hn).1
  · exact Erdos848.originalA18_nonSquarefree N

theorem residue_class_cardinalities (N : ℕ) :
    (Erdos848.OriginalA7 N).card = (N + 18) / 25 ∧
      (Erdos848.OriginalA18 N).card = (N + 7) / 25 := by
  exact ⟨Erdos848.originalA7_card_exact N,
    Erdos848.originalA18_card_exact N⟩

end Erdos848Completion
