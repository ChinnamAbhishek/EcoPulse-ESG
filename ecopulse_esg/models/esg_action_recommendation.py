# -*- coding: utf-8 -*-

from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class EcoPulseESGActionRecommendation(models.Model):
    """
    Smart ESG Action Recommendation Engine.

    Recommendations can be generated from:
    - Carbon budget performance
    - Emission anomalies
    - Greenwashing risk
    - Carbon trust score
    - High-emission transactions
    """

    _name = "ecopulse.esg.action.recommendation"
    _description = "EcoPulse ESG Action Recommendation"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "priority_rank, target_date, id desc"

    # ---------------------------------------------------------
    # Main Information
    # ---------------------------------------------------------

    name = fields.Char(
        string="Recommendation Reference",
        required=True,
        readonly=True,
        copy=False,
        default="New",
        tracking=True,
    )

    title = fields.Char(
        string="Action Title",
        required=True,
        tracking=True,
    )

    description = fields.Text(
        string="Recommended Action",
        required=True,
        tracking=True,
    )

    recommendation_source = fields.Selection(
        selection=[
            ("budget", "Carbon Budget"),
            ("anomaly", "Emission Anomaly"),
            ("trust", "Carbon Trust Score"),
            ("greenwashing", "Greenwashing Risk"),
            ("high_emission", "High Emission"),
            ("manual", "Manual Recommendation"),
        ],
        string="Recommendation Source",
        required=True,
        default="manual",
        tracking=True,
    )

    priority = fields.Selection(
        selection=[
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
            ("critical", "Critical"),
        ],
        string="Priority",
        required=True,
        default="medium",
        tracking=True,
    )

    priority_rank = fields.Integer(
        string="Priority Rank",
        compute="_compute_priority_rank",
        store=True,
    )

    status = fields.Selection(
        selection=[
            ("proposed", "Proposed"),
            ("approved", "Approved"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
            ("rejected", "Rejected"),
        ],
        string="Status",
        required=True,
        default="proposed",
        tracking=True,
    )

    # ---------------------------------------------------------
    # Responsibility and Timeline
    # ---------------------------------------------------------

    department_id = fields.Many2one(
        comodel_name="ecopulse.department",
        string="Responsible Department",
        tracking=True,
    )

    responsible_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsible Person",
        tracking=True,
    )

    generated_date = fields.Date(
        string="Generated Date",
        default=fields.Date.today,
        required=True,
        tracking=True,
    )

    target_date = fields.Date(
        string="Target Date",
        default=lambda self: fields.Date.today() + timedelta(days=30),
        required=True,
        tracking=True,
    )

    completed_date = fields.Date(
        string="Completed Date",
        readonly=True,
        tracking=True,
    )

    # ---------------------------------------------------------
    # Environmental Impact
    # ---------------------------------------------------------

    baseline_emission = fields.Float(
        string="Baseline Emission",
        digits=(16, 4),
        tracking=True,
    )

    expected_reduction_percent = fields.Float(
        string="Expected Reduction %",
        digits=(16, 2),
        tracking=True,
    )

    expected_reduction_emission = fields.Float(
        string="Expected Reduction",
        compute="_compute_expected_reduction",
        store=True,
        digits=(16, 4),
    )

    projected_emission = fields.Float(
        string="Projected Emission",
        compute="_compute_expected_reduction",
        store=True,
        digits=(16, 4),
    )

    actual_reduction_emission = fields.Float(
        string="Actual Reduction",
        digits=(16, 4),
        tracking=True,
    )

    impact_score = fields.Integer(
        string="Impact Score",
        compute="_compute_impact_score",
        store=True,
        help="Estimated environmental impact score from 0 to 100.",
    )

    # ---------------------------------------------------------
    # Linked Records
    # ---------------------------------------------------------

    carbon_transaction_id = fields.Many2one(
        comodel_name="ecopulse.carbon.transaction",
        string="Related Carbon Transaction",
        ondelete="set null",
    )

    carbon_budget_id = fields.Many2one(
        comodel_name="ecopulse.carbon.budget",
        string="Related Carbon Budget",
        ondelete="set null",
    )

    # ---------------------------------------------------------
    # Recommendation Details
    # ---------------------------------------------------------

    problem_detected = fields.Text(
        string="Problem Detected",
        tracking=True,
    )

    expected_benefit = fields.Text(
        string="Expected Benefit",
        tracking=True,
    )

    implementation_steps = fields.Text(
        string="Implementation Steps",
        tracking=True,
    )

    verification_method = fields.Text(
        string="Verification Method",
        tracking=True,
    )

    management_note = fields.Text(
        string="Management Note",
        tracking=True,
    )

    active = fields.Boolean(
        default=True,
    )

    # ---------------------------------------------------------
    # Sequence
    # ---------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code(
                        "ecopulse.esg.action.recommendation"
                    )
                    or "New"
                )

        return super().create(vals_list)

    # ---------------------------------------------------------
    # Computed Fields
    # ---------------------------------------------------------

    @api.depends("priority")
    def _compute_priority_rank(self):
        rank_map = {
            "critical": 1,
            "high": 2,
            "medium": 3,
            "low": 4,
        }

        for record in self:
            record.priority_rank = rank_map.get(
                record.priority,
                5,
            )

    @api.depends(
        "baseline_emission",
        "expected_reduction_percent",
    )
    def _compute_expected_reduction(self):
        for record in self:
            baseline = record.baseline_emission or 0.0
            percentage = (
                record.expected_reduction_percent or 0.0
            )

            reduction = baseline * percentage / 100

            record.expected_reduction_emission = reduction
            record.projected_emission = max(
                0.0,
                baseline - reduction,
            )

    @api.depends(
        "expected_reduction_percent",
        "expected_reduction_emission",
        "priority",
    )
    def _compute_impact_score(self):
        priority_bonus = {
            "low": 0,
            "medium": 5,
            "high": 10,
            "critical": 15,
        }

        for record in self:
            percentage_score = min(
                60,
                int(
                    record.expected_reduction_percent
                    or 0.0
                ) * 2,
            )

            emission_score = min(
                25,
                int(
                    (
                        record.expected_reduction_emission
                        or 0.0
                    )
                    / 100
                ),
            )

            score = (
                percentage_score
                + emission_score
                + priority_bonus.get(record.priority, 0)
            )

            record.impact_score = max(
                0,
                min(100, score),
            )

    # ---------------------------------------------------------
    # Constraints
    # ---------------------------------------------------------

    @api.constrains("expected_reduction_percent")
    def _check_expected_reduction_percent(self):
        for record in self:
            if not (
                0
                <= record.expected_reduction_percent
                <= 100
            ):
                raise ValidationError(
                    "Expected Reduction Percentage must be "
                    "between 0 and 100."
                )

    @api.constrains(
        "generated_date",
        "target_date",
    )
    def _check_target_date(self):
        for record in self:
            if (
                record.generated_date
                and record.target_date
                and record.target_date < record.generated_date
            ):
                raise ValidationError(
                    "Target Date cannot be earlier than "
                    "Generated Date."
                )
    # ---------------------------------------------------------
    # Smart Recommendation Generator
    # ---------------------------------------------------------

    def action_generate_smart_recommendation(self):
        for record in self:
            baseline = record.baseline_emission or 0.0
            reduction_percent = (
                record.expected_reduction_percent or 0.0
            )
            source = record.recommendation_source or "manual"

            source_content = {
                "budget": {
                    "title": "Reduce Carbon Budget Overrun",
                    "problem": (
                        "The selected department is approaching or "
                        "exceeding its approved carbon-emission budget."
                    ),
                    "action": (
                        "Review the department's major emission sources, "
                        "prioritize high-impact reduction opportunities, "
                        "and introduce monthly carbon-budget controls."
                    ),
                    "benefit": (
                        "Improves carbon-budget compliance, reduces "
                        "avoidable emissions, and supports timely "
                        "management decisions."
                    ),
                    "steps": (
                        "1. Review current carbon-budget utilization.\n"
                        "2. Identify the top emission contributors.\n"
                        "3. Assign reduction responsibilities.\n"
                        "4. Implement reduction measures.\n"
                        "5. Review progress every month."
                    ),
                    "verification": (
                        "Compare monthly actual emissions against the "
                        "approved carbon budget and projected emissions."
                    ),
                },
                "anomaly": {
                    "title": "Investigate Abnormal Emission Increase",
                    "problem": (
                        "EcoPulse detected an unusual increase in carbon "
                        "emissions compared with the normal operating pattern."
                    ),
                    "action": (
                        "Investigate the abnormal transaction or activity, "
                        "verify the recorded data, and correct the operational "
                        "cause responsible for the emission spike."
                    ),
                    "benefit": (
                        "Prevents repeated emission spikes, improves data "
                        "accuracy, and enables faster corrective action."
                    ),
                    "steps": (
                        "1. Validate the abnormal emission record.\n"
                        "2. Compare it with historical activity.\n"
                        "3. Identify the operational root cause.\n"
                        "4. Apply corrective controls.\n"
                        "5. Monitor the next reporting period."
                    ),
                    "verification": (
                        "Confirm that subsequent emission values return to "
                        "the expected range and verify the source data."
                    ),
                },
                "trust": {
                    "title": "Improve Carbon Trust Performance",
                    "problem": (
                        "The current carbon trust score indicates that ESG "
                        "performance, evidence, or reporting quality requires "
                        "improvement."
                    ),
                    "action": (
                        "Improve emission-data quality, attach supporting "
                        "evidence, complete pending sustainability actions, "
                        "and strengthen review controls."
                    ),
                    "benefit": (
                        "Improves ESG credibility, transparency, audit "
                        "readiness, and stakeholder confidence."
                    ),
                    "steps": (
                        "1. Review trust-score weaknesses.\n"
                        "2. Validate carbon records.\n"
                        "3. Attach supporting evidence.\n"
                        "4. Resolve incomplete ESG actions.\n"
                        "5. Recalculate and review the score."
                    ),
                    "verification": (
                        "Recalculate the carbon trust score and confirm that "
                        "the identified weaknesses have been resolved."
                    ),
                },
                "greenwashing": {
                    "title": "Resolve Greenwashing Risk",
                    "problem": (
                        "EcoPulse identified a possible mismatch between "
                        "reported sustainability claims and supporting "
                        "emission evidence."
                    ),
                    "action": (
                        "Review the sustainability claim, verify supporting "
                        "records, correct unsupported statements, and obtain "
                        "management approval before publication."
                    ),
                    "benefit": (
                        "Reduces reputational risk, improves reporting "
                        "accuracy, and strengthens ESG transparency."
                    ),
                    "steps": (
                        "1. Review the flagged sustainability claim.\n"
                        "2. Collect supporting emission evidence.\n"
                        "3. Compare the claim with actual performance.\n"
                        "4. Correct unsupported information.\n"
                        "5. Obtain management approval."
                    ),
                    "verification": (
                        "Confirm that every sustainability claim is supported "
                        "by verified records and measurable results."
                    ),
                },
                "high_emission": {
                    "title": "Reduce High-Emission Activity",
                    "problem": (
                        "A high-emission activity or transaction is creating "
                        "a significant environmental impact."
                    ),
                    "action": (
                        "Optimize the activity, replace inefficient resources, "
                        "introduce lower-carbon alternatives, and continuously "
                        "track emission performance."
                    ),
                    "benefit": (
                        "Reduces carbon emissions, operating costs, and "
                        "dependence on inefficient processes."
                    ),
                    "steps": (
                        "1. Identify the high-emission source.\n"
                        "2. Evaluate low-carbon alternatives.\n"
                        "3. Select the most practical reduction measure.\n"
                        "4. Implement the selected measure.\n"
                        "5. Measure the achieved reduction."
                    ),
                    "verification": (
                        "Compare baseline emissions with actual emissions "
                        "after implementation."
                    ),
                },
                "manual": {
                    "title": "Implement Sustainability Improvement",
                    "problem": (
                        "A sustainability improvement opportunity requires "
                        "structured corrective action."
                    ),
                    "action": (
                        "Define the environmental issue, assign an owner, "
                        "implement measurable improvement actions, and monitor "
                        "the results."
                    ),
                    "benefit": (
                        "Improves environmental performance and creates a "
                        "clear, measurable sustainability workflow."
                    ),
                    "steps": (
                        "1. Define the sustainability issue.\n"
                        "2. Assign a responsible owner.\n"
                        "3. Implement the corrective action.\n"
                        "4. Monitor environmental performance.\n"
                        "5. Verify and document the result."
                    ),
                    "verification": (
                        "Compare the measured result with the original "
                        "baseline and the expected reduction target."
                    ),
                },
            }

            content = source_content.get(
                source,
                source_content["manual"],
            )

            priority = "medium"

            if baseline >= 10000:
                priority = "critical"
            elif baseline >= 5000:
                priority = "high"
            elif baseline > 0:
                priority = "medium"
            else:
                priority = record.priority or "medium"

            record.write({
                "title": content["title"],
                "priority": priority,
                "problem_detected": content["problem"],
                "description": content["action"],
                "expected_benefit": content["benefit"],
                "implementation_steps": content["steps"],
                "verification_method": content["verification"],
            })

            record.message_post(
                body=(
                    "Smart ESG recommendation generated automatically. "
                    f"Baseline emission: {baseline:.2f} kg CO2e. "
                    f"Expected reduction target: "
                    f"{reduction_percent:.2f}%."
                )
            )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Smart Recommendation Generated",
                "message": (
                    "EcoPulse generated the action title, priority, "
                    "problem, recommendation, benefits, implementation "
                    "steps, and verification method."
                ),
                "type": "success",
                "sticky": False,
            },
        }
    # ---------------------------------------------------------
    # Workflow Actions
    # ---------------------------------------------------------

    def action_approve(self):
        self.write({
            "status": "approved",
        })

        return True

    def action_start(self):
        self.write({
            "status": "in_progress",
        })

        return True

    def action_complete(self):
        self.write({
            "status": "completed",
            "completed_date": fields.Date.today(),
        })

        return True

    def action_reject(self):
        self.write({
            "status": "rejected",
        })

        return True

    def action_reset_to_proposed(self):
        self.write({
            "status": "proposed",
            "completed_date": False,
        })

        return True

    def action_open_source_record(self):
        self.ensure_one()

        if self.carbon_transaction_id:
            return {
                "type": "ir.actions.act_window",
                "name": "Carbon Transaction",
                "res_model": "ecopulse.carbon.transaction",
                "res_id": self.carbon_transaction_id.id,
                "view_mode": "form",
                "target": "current",
            }

        if self.carbon_budget_id:
            return {
                "type": "ir.actions.act_window",
                "name": "Carbon Budget",
                "res_model": "ecopulse.carbon.budget",
                "res_id": self.carbon_budget_id.id,
                "view_mode": "form",
                "target": "current",
            }

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "No Linked Record",
                "message": (
                    "This recommendation has no linked "
                    "transaction or carbon budget."
                ),
                "type": "warning",
                "sticky": False,
            },
        }