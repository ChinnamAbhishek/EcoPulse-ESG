# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class EcoPulseESGActionROI(models.Model):
    """
    Calculates the financial value and ROI of ESG actions
    using expected and actual carbon-emission reductions.
    """

    _inherit = "ecopulse.esg.action.recommendation"

    implementation_cost = fields.Monetary(
        string="Implementation Cost",
        currency_field="currency_id",
        tracking=True,
    )

    carbon_price_per_ton = fields.Monetary(
        string="Carbon Price per Ton",
        currency_field="currency_id",
        default=2500.0,
        tracking=True,
        help="Financial value assigned to one ton of CO2e reduction.",
    )

    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )

    expected_carbon_value = fields.Monetary(
        string="Expected Carbon Value",
        currency_field="currency_id",
        compute="_compute_esg_roi",
        store=True,
    )

    actual_carbon_value = fields.Monetary(
        string="Actual Carbon Value",
        currency_field="currency_id",
        compute="_compute_esg_roi",
        store=True,
    )

    expected_net_benefit = fields.Monetary(
        string="Expected Net Benefit",
        currency_field="currency_id",
        compute="_compute_esg_roi",
        store=True,
    )

    actual_net_benefit = fields.Monetary(
        string="Actual Net Benefit",
        currency_field="currency_id",
        compute="_compute_esg_roi",
        store=True,
    )

    expected_roi_percent = fields.Float(
        string="Expected ESG ROI %",
        compute="_compute_esg_roi",
        store=True,
        digits=(16, 2),
    )

    actual_roi_percent = fields.Float(
        string="Actual ESG ROI %",
        compute="_compute_esg_roi",
        store=True,
        digits=(16, 2),
    )

    roi_status = fields.Selection(
        selection=[
            ("not_calculated", "Not Calculated"),
            ("negative", "Negative Return"),
            ("break_even", "Break Even"),
            ("positive", "Positive Return"),
            ("high_return", "High Return"),
        ],
        string="ROI Status",
        compute="_compute_esg_roi",
        store=True,
    )

    roi_summary = fields.Text(
        string="ROI Intelligence Summary",
        compute="_compute_esg_roi",
        store=True,
    )

    @api.depends(
        "implementation_cost",
        "carbon_price_per_ton",
        "expected_reduction_emission",
        "actual_reduction_emission",
    )
    def _compute_esg_roi(self):
        for record in self:
            cost = record.implementation_cost or 0.0
            carbon_price = record.carbon_price_per_ton or 0.0

            expected_tons = (
                record.expected_reduction_emission or 0.0
            ) / 1000.0

            actual_tons = (
                record.actual_reduction_emission or 0.0
            ) / 1000.0

            expected_value = expected_tons * carbon_price
            actual_value = actual_tons * carbon_price

            expected_net = expected_value - cost
            actual_net = actual_value - cost

            expected_roi = 0.0
            actual_roi = 0.0

            if cost > 0:
                expected_roi = expected_net / cost * 100
                actual_roi = actual_net / cost * 100

            if cost <= 0 or carbon_price <= 0:
                status = "not_calculated"
                summary = (
                    "Enter the implementation cost and carbon price "
                    "to calculate ESG financial returns."
                )

            elif actual_net < 0:
                status = "negative"
                summary = (
                    f"The action currently has a negative net return of "
                    f"{abs(actual_net):.2f}."
                )

            elif abs(actual_net) < 0.01:
                status = "break_even"
                summary = (
                    "The action has reached its financial break-even point."
                )

            elif actual_roi >= 50:
                status = "high_return"
                summary = (
                    f"The action generated a high ESG return of "
                    f"{actual_roi:.2f}%."
                )

            else:
                status = "positive"
                summary = (
                    f"The action generated a positive ESG return of "
                    f"{actual_roi:.2f}%."
                )

            record.expected_carbon_value = expected_value
            record.actual_carbon_value = actual_value
            record.expected_net_benefit = expected_net
            record.actual_net_benefit = actual_net
            record.expected_roi_percent = expected_roi
            record.actual_roi_percent = actual_roi
            record.roi_status = status
            record.roi_summary = summary

    @api.constrains(
        "implementation_cost",
        "carbon_price_per_ton",
    )
    def _check_roi_values(self):
        for record in self:
            if record.implementation_cost < 0:
                raise ValidationError(
                    "Implementation Cost cannot be negative."
                )

            if record.carbon_price_per_ton < 0:
                raise ValidationError(
                    "Carbon Price per Ton cannot be negative."
                )

    def action_calculate_esg_roi(self):
        self.ensure_one()

        if self.implementation_cost <= 0:
            raise ValidationError(
                "Enter the Implementation Cost before calculating ROI."
            )

        if self.carbon_price_per_ton <= 0:
            raise ValidationError(
                "Enter a valid Carbon Price per Ton."
            )

        self._compute_esg_roi()

        self.message_post(
            body=(
                f"ESG ROI calculated. "
                f"Expected ROI: {self.expected_roi_percent:.2f}%. "
                f"Actual ROI: {self.actual_roi_percent:.2f}%."
            )
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "ESG ROI Calculated",
                "message": (
                    f"Actual net benefit: "
                    f"{self.actual_net_benefit:.2f}. "
                    f"Actual ROI: "
                    f"{self.actual_roi_percent:.2f}%."
                ),
                "type": (
                    "success"
                    if self.actual_net_benefit >= 0
                    else "warning"
                ),
                "sticky": False,
            },
        }