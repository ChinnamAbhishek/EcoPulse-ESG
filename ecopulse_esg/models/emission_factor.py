from odoo import api, fields, models
from odoo.exceptions import ValidationError


class EcoPulseEmissionFactor(models.Model):
    _name = "ecopulse.emission.factor"
    _description = "ESG Emission Factor"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"

    name = fields.Char(
        string="Factor Name",
        required=True,
        tracking=True,
    )

    source_type = fields.Selection(
        selection=[
            ("diesel", "Diesel"),
            ("petrol", "Petrol"),
            ("electricity", "Electricity"),
            ("fleet", "Fleet"),
            ("flight", "Flight"),
            ("purchase", "Purchase"),
            ("manufacturing", "Manufacturing"),
            ("expense", "Expense"),
            ("waste", "Waste"),
            ("other", "Other"),
        ],
        string="Source Type",
        required=True,
        tracking=True,
    )

    unit = fields.Selection(
        selection=[
            ("litre", "Litre"),
            ("kwh", "kWh"),
            ("kg", "Kilogram"),
            ("km", "Kilometre"),
            ("passenger_km", "Passenger Kilometre"),
            ("unit", "Unit"),
        ],
        string="Activity Unit",
        required=True,
    )

    factor_value = fields.Float(
        string="Emission Factor",
        required=True,
        digits=(16, 6),
        tracking=True,
    )

    factor_unit = fields.Char(
        string="Factor Unit",
        default="kg CO2e",
        required=True,
    )

    scope = fields.Selection(
        selection=[
            ("scope_1", "Scope 1"),
            ("scope_2", "Scope 2"),
            ("scope_3", "Scope 3"),
        ],
        string="Emission Scope",
        required=True,
        tracking=True,
    )

    region = fields.Char(
        string="Region",
        default="India",
    )

    valid_from = fields.Date(
        string="Valid From",
        default=fields.Date.context_today,
        required=True,
    )

    valid_to = fields.Date(
        string="Valid To",
    )

    status = fields.Selection(
        selection=[
            ("active", "Active"),
            ("inactive", "Inactive"),
        ],
        string="Status",
        default="active",
        required=True,
        tracking=True,
    )

    notes = fields.Text(string="Notes")

    @api.constrains("factor_value")
    def _check_factor_value(self):
        for factor in self:
            if factor.factor_value <= 0:
                raise ValidationError(
                    "Emission factor must be greater than zero."
                )

    @api.constrains("valid_from", "valid_to")
    def _check_dates(self):
        for factor in self:
            if (
                factor.valid_from
                and factor.valid_to
                and factor.valid_to < factor.valid_from
            ):
                raise ValidationError(
                    "Valid To cannot be earlier than Valid From."
                )