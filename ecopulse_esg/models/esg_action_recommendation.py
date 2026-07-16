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