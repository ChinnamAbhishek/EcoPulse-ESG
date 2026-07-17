# -*- coding: utf-8 -*-

from odoo import api, fields, models


class EcoPulseESGActionRisk(models.Model):
    """
    Predicts implementation risk for ESG actions before execution.
    """

    _inherit = "ecopulse.esg.action.recommendation"

    risk_score = fields.Integer(
        string="Implementation Risk Score",
        compute="_compute_action_risk",
        store=True,
        help="Predicted action implementation risk from 0 to 100.",
    )

    risk_level = fields.Selection(
        selection=[
            ("low", "Low Risk"),
            ("medium", "Medium Risk"),
            ("high", "High Risk"),
            ("critical", "Critical Risk"),
        ],
        string="Implementation Risk",
        compute="_compute_action_risk",
        store=True,
        tracking=True,
    )

    risk_reasons = fields.Text(
        string="Risk Reasons",
        compute="_compute_action_risk",
        store=True,
    )

    preventive_recommendation = fields.Text(
        string="Preventive Recommendation",
        compute="_compute_action_risk",
        store=True,
    )

    @api.depends(
        "priority",
        "baseline_emission",
        "expected_reduction_percent",
        "generated_date",
        "target_date",
        "responsible_user_id",
        "department_id",
    )
    def _compute_action_risk(self):
        for record in self:
            score = 0
            reasons = []
            recommendations = []

            priority_score = {
                "low": 5,
                "medium": 10,
                "high": 20,
                "critical": 30,
            }

            score += priority_score.get(record.priority, 10)

            if record.baseline_emission >= 10000:
                score += 25
                reasons.append(
                    "The baseline emission is extremely high."
                )
                recommendations.append(
                    "Break the action into smaller measurable phases."
                )
            elif record.baseline_emission >= 5000:
                score += 18
                reasons.append(
                    "The baseline emission is high."
                )
                recommendations.append(
                    "Assign additional resources and conduct weekly reviews."
                )
            elif record.baseline_emission >= 1000:
                score += 10
                reasons.append(
                    "The baseline emission requires close monitoring."
                )

            if record.expected_reduction_percent >= 50:
                score += 20
                reasons.append(
                    "The expected reduction target is highly ambitious."
                )
                recommendations.append(
                    "Validate the target using historical performance data."
                )
            elif record.expected_reduction_percent >= 30:
                score += 12
                reasons.append(
                    "The expected reduction target is ambitious."
                )

            if not record.responsible_user_id:
                score += 15
                reasons.append(
                    "No responsible owner has been assigned."
                )
                recommendations.append(
                    "Assign a responsible owner before starting the action."
                )

            if not record.department_id:
                score += 10
                reasons.append(
                    "No responsible department has been assigned."
                )
                recommendations.append(
                    "Assign the action to a responsible department."
                )

            if record.generated_date and record.target_date:
                duration = (
                    record.target_date - record.generated_date
                ).days

                if duration <= 7:
                    score += 20
                    reasons.append(
                        "The implementation timeline is extremely short."
                    )
                    recommendations.append(
                        "Extend the target date or increase implementation resources."
                    )
                elif duration <= 15:
                    score += 12
                    reasons.append(
                        "The implementation timeline is short."
                    )

            score = max(0, min(100, score))

            if score >= 75:
                level = "critical"
            elif score >= 50:
                level = "high"
            elif score >= 25:
                level = "medium"
            else:
                level = "low"

            if not reasons:
                reasons.append(
                    "No major implementation risks were detected."
                )

            if not recommendations:
                recommendations.append(
                    "Continue normal monitoring and periodic progress reviews."
                )

            record.risk_score = score
            record.risk_level = level
            record.risk_reasons = "\n".join(
                f"• {reason}" for reason in reasons
            )
            record.preventive_recommendation = "\n".join(
                f"• {recommendation}"
                for recommendation in recommendations
            )

    def action_analyze_risk(self):
        self.ensure_one()

        self._compute_action_risk()

        self.message_post(
            body=(
                f"Implementation risk analyzed. "
                f"Risk score: {self.risk_score}/100. "
                f"Risk level: {self.risk_level}."
            )
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Risk Prediction Generated",
                "message": (
                    f"Implementation risk score: "
                    f"{self.risk_score}/100. "
                    f"Risk level: {self.risk_level}."
                ),
                "type": (
                    "danger"
                    if self.risk_level == "critical"
                    else "warning"
                    if self.risk_level == "high"
                    else "success"
                ),
                "sticky": False,
            },
        }