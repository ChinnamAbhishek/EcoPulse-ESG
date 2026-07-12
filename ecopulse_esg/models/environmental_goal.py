from odoo import api, fields, models
from odoo.exceptions import ValidationError


class EcoPulseEnvironmentalGoal(models.Model):
    _name = "ecopulse.environmental.goal"
    _description = "Environmental Sustainability Goal"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "end_date, name"

    name = fields.Char(
        string="Goal Name",
        required=True,
        tracking=True,
    )

    department_id = fields.Many2one(
        comodel_name="ecopulse.department",
        string="Department",
        required=True,
        ondelete="cascade",
        tracking=True,
    )

    metric_type = fields.Selection(
        selection=[
            ("emission_reduction", "Emission Reduction"),
            ("renewable_energy", "Renewable Energy"),
            ("waste_reduction", "Waste Reduction"),
            ("water_conservation", "Water Conservation"),
            ("energy_efficiency", "Energy Efficiency"),
            ("other", "Other"),
        ],
        string="Metric Type",
        required=True,
        tracking=True,
    )

    baseline_value = fields.Float(
        string="Baseline Value",
        required=True,
    )

    target_value = fields.Float(
        string="Target Value",
        required=True,
    )

    current_value = fields.Float(
        string="Current Value",
        default=0.0,
        tracking=True,
    )

    start_date = fields.Date(
        string="Start Date",
        required=True,
        default=fields.Date.context_today,
    )

    end_date = fields.Date(
        string="End Date",
        required=True,
        tracking=True,
    )

    progress_percentage = fields.Float(
        string="Progress (%)",
        compute="_compute_progress",
        store=True,
    )

    status = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("active", "Active"),
            ("completed", "Completed"),
            ("at_risk", "At Risk"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        compute="_compute_status",
        store=True,
        readonly=False,
        tracking=True,
    )

    risk_level = fields.Selection(
        selection=[
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
        ],
        string="Risk Level",
        compute="_compute_status",
        store=True,
    )

    description = fields.Text(string="Description")

    @api.depends(
        "baseline_value",
        "target_value",
        "current_value",
    )
    def _compute_progress(self):
        for goal in self:
            difference = goal.baseline_value - goal.target_value

            if difference == 0:
                goal.progress_percentage = (
                    100.0
                    if goal.current_value == goal.target_value
                    else 0.0
                )
                continue

            # Reduction-type goal:
            # Baseline 10000, target 8000, current 9000 = 50% progress.
            progress = (
                (goal.baseline_value - goal.current_value)
                / difference
            ) * 100

            goal.progress_percentage = round(
                max(0.0, min(progress, 100.0)),
                2,
            )

    @api.depends("progress_percentage", "end_date")
    def _compute_status(self):
        today = fields.Date.context_today(self)

        for goal in self:
            if goal.status == "cancelled":
                goal.risk_level = "low"
                continue

            if goal.progress_percentage >= 100:
                goal.status = "completed"
                goal.risk_level = "low"
            elif goal.end_date and goal.end_date < today:
                goal.status = "at_risk"
                goal.risk_level = "high"
            elif goal.progress_percentage < 40:
                goal.status = "active"
                goal.risk_level = "medium"
            else:
                goal.status = "active"
                goal.risk_level = "low"

    @api.constrains("start_date", "end_date")
    def _check_dates(self):
        for goal in self:
            if (
                goal.start_date
                and goal.end_date
                and goal.end_date < goal.start_date
            ):
                raise ValidationError(
                    "Goal end date cannot be earlier than start date."
                )

    @api.constrains(
        "baseline_value",
        "target_value",
        "current_value",
    )
    def _check_values(self):
        for goal in self:
            if min(
                goal.baseline_value,
                goal.target_value,
                goal.current_value,
            ) < 0:
                raise ValidationError(
                    "Goal values cannot be negative."
                )