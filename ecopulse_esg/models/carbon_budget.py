# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class EcoPulseCarbonBudget(models.Model):
    """
    Department-level carbon budget.

    It compares the assigned carbon-emission allowance with actual
    carbon transactions recorded during the selected period.
    """

    _name = "ecopulse.carbon.budget"
    _description = "EcoPulse Department Carbon Budget"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "start_date desc, department_id"

    name = fields.Char(
        string="Budget Reference",
        required=True,
        copy=False,
        readonly=True,
        default="New",
        tracking=True,
    )

    department_id = fields.Many2one(
        comodel_name="ecopulse.department",
        string="Department",
        required=True,
        tracking=True,
        ondelete="cascade",
    )

    start_date = fields.Date(
        string="Start Date",
        required=True,
        tracking=True,
    )

    end_date = fields.Date(
        string="End Date",
        required=True,
        tracking=True,
    )

    budget_emission = fields.Float(
        string="Carbon Budget",
        required=True,
        digits=(16, 4),
        tracking=True,
        help="Maximum permitted emissions for this department in kg CO₂e.",
    )

    warning_threshold_percent = fields.Float(
        string="Warning Threshold %",
        default=80.0,
        required=True,
        tracking=True,
        help=(
            "An early warning is triggered when budget usage reaches "
            "this percentage."
        ),
    )

    include_draft_transactions = fields.Boolean(
        string="Include Draft Transactions",
        default=False,
        tracking=True,
    )

    actual_emission = fields.Float(
        string="Actual Emission",
        compute="_compute_budget_performance",
        store=True,
        digits=(16, 4),
    )

    remaining_budget = fields.Float(
        string="Remaining Budget",
        compute="_compute_budget_performance",
        store=True,
        digits=(16, 4),
    )

    budget_usage_percent = fields.Float(
        string="Budget Usage %",
        compute="_compute_budget_performance",
        store=True,
        digits=(16, 2),
    )

    exceeded_emission = fields.Float(
        string="Exceeded By",
        compute="_compute_budget_performance",
        store=True,
        digits=(16, 4),
    )

    transaction_count = fields.Integer(
        string="Transactions",
        compute="_compute_budget_performance",
        store=True,
    )

    budget_status = fields.Selection(
        selection=[
            ("safe", "Within Budget"),
            ("warning", "Warning"),
            ("exceeded", "Exceeded"),
            ("critical", "Critical"),
        ],
        string="Budget Status",
        compute="_compute_budget_performance",
        store=True,
        tracking=True,
    )

    alert_message = fields.Text(
        string="Budget Alert",
        compute="_compute_budget_performance",
        store=True,
    )

    active = fields.Boolean(
        default=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code(
                        "ecopulse.carbon.budget"
                    )
                    or "New"
                )

        return super().create(vals_list)

    @api.constrains(
        "start_date",
        "end_date",
    )
    def _check_dates(self):
        for record in self:
            if (
                record.start_date
                and record.end_date
                and record.start_date > record.end_date
            ):
                raise ValidationError(
                    "Start Date cannot be later than End Date."
                )

    @api.constrains("budget_emission")
    def _check_budget_emission(self):
        for record in self:
            if record.budget_emission <= 0:
                raise ValidationError(
                    "Carbon Budget must be greater than zero."
                )

    @api.constrains("warning_threshold_percent")
    def _check_warning_threshold(self):
        for record in self:
            if not 1 <= record.warning_threshold_percent <= 100:
                raise ValidationError(
                    "Warning Threshold must be between 1 and 100."
                )

    @api.depends(
        "department_id",
        "start_date",
        "end_date",
        "budget_emission",
        "warning_threshold_percent",
        "include_draft_transactions",
    )
    def _compute_budget_performance(self):
        transaction_model = self.env[
            "ecopulse.carbon.transaction"
        ]

        for record in self:
            actual_emission = 0.0
            transaction_count = 0

            if (
                record.department_id
                and record.start_date
                and record.end_date
            ):
                domain = [
                    (
                        "department_id",
                        "=",
                        record.department_id.id,
                    ),
                    (
                        "transaction_date",
                        ">=",
                        record.start_date,
                    ),
                    (
                        "transaction_date",
                        "<=",
                        record.end_date,
                    ),
                    (
                        "status",
                        "!=",
                        "cancelled",
                    ),
                ]

                if not record.include_draft_transactions:
                    domain.append(
                        (
                            "status",
                            "in",
                            ["calculated", "verified"],
                        )
                    )

                transactions = transaction_model.search(domain)

                actual_emission = sum(
                    transactions.mapped(
                        "calculated_emission"
                    )
                )

                transaction_count = len(transactions)

            budget = record.budget_emission or 0.0

            usage_percent = (
                actual_emission / budget * 100
                if budget > 0
                else 0.0
            )

            remaining_budget = budget - actual_emission

            exceeded_emission = max(
                0.0,
                actual_emission - budget,
            )

            if usage_percent >= 125:
                budget_status = "critical"
                alert_message = (
                    f"Critical: {record.department_id.display_name or 'Department'} "
                    f"has used {usage_percent:.2f}% of its carbon budget and "
                    f"exceeded the limit by {exceeded_emission:,.2f} kg CO₂e."
                )

            elif usage_percent > 100:
                budget_status = "exceeded"
                alert_message = (
                    f"Budget exceeded: emissions are "
                    f"{exceeded_emission:,.2f} kg CO₂e above the assigned limit."
                )

            elif usage_percent >= (
                record.warning_threshold_percent or 80.0
            ):
                budget_status = "warning"
                alert_message = (
                    f"Warning: {usage_percent:.2f}% of the carbon budget "
                    "has already been consumed."
                )

            else:
                budget_status = "safe"
                alert_message = (
                    f"Carbon budget is under control. "
                    f"{max(remaining_budget, 0.0):,.2f} kg CO₂e remains."
                )

            record.actual_emission = actual_emission
            record.remaining_budget = remaining_budget
            record.budget_usage_percent = usage_percent
            record.exceeded_emission = exceeded_emission
            record.transaction_count = transaction_count
            record.budget_status = budget_status
            record.alert_message = alert_message

    def action_refresh_budget(self):
        self._compute_budget_performance()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Carbon Budget Updated",
                "message": (
                    "Actual emissions and budget usage were recalculated."
                ),
                "type": "success",
                "sticky": False,
            },
        }

    def action_view_transactions(self):
        self.ensure_one()

        domain = [
            (
                "department_id",
                "=",
                self.department_id.id,
            ),
            (
                "transaction_date",
                ">=",
                self.start_date,
            ),
            (
                "transaction_date",
                "<=",
                self.end_date,
            ),
            (
                "status",
                "!=",
                "cancelled",
            ),
        ]

        return {
            "type": "ir.actions.act_window",
            "name": "Budget Carbon Transactions",
            "res_model": "ecopulse.carbon.transaction",
            "view_mode": "list,form,graph,pivot",
            "domain": domain,
            "context": {
                "default_department_id": self.department_id.id,
            },
        }