# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class EcoPulseESGActionOutcome(models.Model):
    """
    ESG Action Outcome Intelligence.

    Compares expected emission reduction with actual reduction
    and evaluates the effectiveness of completed ESG actions.
    """

    _inherit = "ecopulse.esg.action.recommendation"

    # ---------------------------------------------------------
    # Outcome Intelligence
    # ---------------------------------------------------------

    achievement_percent = fields.Float(
        string="Target Achievement %",
        compute="_compute_outcome_intelligence",
        store=True,
        digits=(16, 2),
        help=(
            "Percentage of expected emission reduction that was "
            "actually achieved."
        ),
    )

    reduction_variance = fields.Float(
        string="Reduction Variance",
        compute="_compute_outcome_intelligence",
        store=True,
        digits=(16, 4),
        help=(
            "Difference between actual reduction and expected reduction."
        ),
    )

    effectiveness_score = fields.Integer(
        string="Effectiveness Score",
        compute="_compute_outcome_intelligence",
        store=True,
        help="Overall ESG action effectiveness score from 0 to 100.",
    )

    outcome_status = fields.Selection(
        selection=[
            ("not_measured", "Not Measured"),
            ("failed", "Failed"),
            ("partial", "Partially Achieved"),
            ("achieved", "Target Achieved"),
            ("exceeded", "Target Exceeded"),
        ],
        string="Outcome Status",
        compute="_compute_outcome_intelligence",
        store=True,
        tracking=True,
    )

    outcome_confidence = fields.Selection(
        selection=[
            ("low", "Low Confidence"),
            ("medium", "Medium Confidence"),
            ("high", "High Confidence"),
        ],
        string="Outcome Confidence",
        compute="_compute_outcome_intelligence",
        store=True,
    )

    outcome_summary = fields.Text(
        string="Outcome Intelligence Summary",
        compute="_compute_outcome_intelligence",
        store=True,
    )

    lessons_learned = fields.Text(
        string="Lessons Learned",
        tracking=True,
        help=(
            "Record implementation lessons to improve future ESG "
            "recommendations."
        ),
    )

    improvement_recommendation = fields.Text(
        string="Improvement Recommendation",
        compute="_compute_outcome_intelligence",
        store=True,
    )

    # ---------------------------------------------------------
    # Outcome Computation
    # ---------------------------------------------------------

    @api.depends(
        "status",
        "expected_reduction_emission",
        "actual_reduction_emission",
        "baseline_emission",
    )
    def _compute_outcome_intelligence(self):
        for record in self:
            expected = record.expected_reduction_emission or 0.0
            actual = record.actual_reduction_emission or 0.0
            baseline = record.baseline_emission or 0.0

            achievement = 0.0
            variance = actual - expected
            effectiveness = 0
            outcome = "not_measured"
            confidence = "low"

            summary = (
                "The ESG action outcome has not yet been measured."
            )

            improvement = (
                "Complete the action and enter the actual emission "
                "reduction to generate outcome intelligence."
            )

            if expected > 0:
                achievement = actual / expected * 100

            if record.status == "completed" and actual >= 0:
                if actual <= 0:
                    outcome = "failed"
                    effectiveness = 0

                    summary = (
                        "The completed ESG action did not produce a "
                        "measurable emission reduction."
                    )

                    improvement = (
                        "Review the implementation process, identify the "
                        "root cause of failure, and redesign the action."
                    )

                elif achievement < 50:
                    outcome = "failed"
                    effectiveness = max(
                        1,
                        min(39, int(achievement)),
                    )

                    summary = (
                        f"The action achieved only {achievement:.2f}% "
                        "of its expected emission-reduction target."
                    )

                    improvement = (
                        "Investigate implementation gaps and introduce "
                        "stronger corrective controls."
                    )

                elif achievement < 90:
                    outcome = "partial"
                    effectiveness = min(
                        74,
                        max(40, int(achievement)),
                    )

                    summary = (
                        f"The action partially achieved its target at "
                        f"{achievement:.2f}%."
                    )

                    improvement = (
                        "Continue monitoring and address the remaining "
                        "performance gap."
                    )

                elif achievement <= 110:
                    outcome = "achieved"
                    effectiveness = min(
                        94,
                        max(75, int(achievement)),
                    )

                    summary = (
                        f"The ESG action successfully achieved "
                        f"{achievement:.2f}% of its target."
                    )

                    improvement = (
                        "Document the successful implementation method "
                        "and reuse it for similar ESG actions."
                    )

                else:
                    outcome = "exceeded"
                    effectiveness = 100

                    summary = (
                        f"The action exceeded its expected target and "
                        f"achieved {achievement:.2f}%."
                    )

                    improvement = (
                        "Capture the success factors and scale the action "
                        "across other departments."
                    )

                if baseline > 0 and expected > 0 and actual > 0:
                    confidence = "high"
                elif expected > 0 and actual > 0:
                    confidence = "medium"
                else:
                    confidence = "low"

            record.achievement_percent = max(
                0.0,
                achievement,
            )

            record.reduction_variance = variance

            record.effectiveness_score = max(
                0,
                min(100, effectiveness),
            )

            record.outcome_status = outcome
            record.outcome_confidence = confidence
            record.outcome_summary = summary
            record.improvement_recommendation = improvement

    # ---------------------------------------------------------
    # Validation
    # ---------------------------------------------------------

    @api.constrains("actual_reduction_emission")
    def _check_actual_reduction_emission(self):
        for record in self:
            if record.actual_reduction_emission < 0:
                raise ValidationError(
                    "Actual Reduction cannot be negative."
                )

            if (
                record.baseline_emission > 0
                and record.actual_reduction_emission
                > record.baseline_emission
            ):
                raise ValidationError(
                    "Actual Reduction cannot be greater than "
                    "Baseline Emission."
                )

    # ---------------------------------------------------------
    # Outcome Action
    # ---------------------------------------------------------

    def action_analyze_outcome(self):
        self.ensure_one()

        if self.status != "completed":
            raise ValidationError(
                "Complete the ESG action before analyzing its outcome."
            )

        if self.actual_reduction_emission <= 0:
            raise ValidationError(
                "Enter the Actual Reduction before analyzing the outcome."
            )

        self._compute_outcome_intelligence()

        self.message_post(
            body=(
                "ESG outcome analyzed. "
                f"Achievement: {self.achievement_percent:.2f}%. "
                f"Effectiveness score: {self.effectiveness_score}/100. "
                f"Outcome: {self.outcome_status}."
            )
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Outcome Intelligence Generated",
                "message": (
                    f"Target achievement: "
                    f"{self.achievement_percent:.2f}%. "
                    f"Effectiveness score: "
                    f"{self.effectiveness_score}/100."
                ),
                "type": "success",
                "sticky": False,
            },
        }