from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class EcoPulseCarbonTransaction(models.Model):
    _name = "ecopulse.carbon.transaction"
    _description = "Carbon Transaction"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "transaction_date desc, id desc"

    reference = fields.Char(
        string="Reference",
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: _("New"),
    )

    source_module = fields.Selection(
        selection=[
            ("purchase", "Purchase"),
            ("fleet", "Fleet"),
            ("manufacturing", "Manufacturing"),
            ("expense", "Expense"),
            ("electricity", "Electricity"),
            ("travel", "Travel"),
            ("waste", "Waste"),
            ("manual", "Manual"),
        ],
        string="Source Module",
        required=True,
        default="manual",
        tracking=True,
    )

    source_record_reference = fields.Char(
        string="Source Record Reference",
        help="Reference of the ERP record that produced this emission.",
    )

    source_record_key = fields.Char(
        string="Unique Source Key",
        copy=False,
        index=True,
        help="Example: purchase.order,25. Used to prevent duplicates.",
    )

    department_id = fields.Many2one(
        comodel_name="ecopulse.department",
        string="Department",
        required=True,
        ondelete="restrict",
        tracking=True,
    )

    activity_quantity = fields.Float(
        string="Activity Quantity",
        required=True,
        digits=(16, 4),
        tracking=True,
    )

    activity_unit = fields.Selection(
        related="emission_factor_id.unit",
        string="Activity Unit",
        store=True,
        readonly=True,
    )

    emission_factor_id = fields.Many2one(
        comodel_name="ecopulse.emission.factor",
        string="Emission Factor",
        required=True,
        domain="[('status', '=', 'active')]",
        ondelete="restrict",
        tracking=True,
    )

    factor_value = fields.Float(
        string="Applied Factor",
        related="emission_factor_id.factor_value",
        store=True,
        readonly=True,
        digits=(16, 6),
    )

    calculated_emission = fields.Float(
        string="Calculated Emission",
        compute="_compute_calculated_emission",
        store=True,
        digits=(16, 4),
        help="Calculated result in kg CO2e.",
    )

    transaction_date = fields.Date(
        string="Transaction Date",
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )

    calculation_method = fields.Selection(
        selection=[
            ("automatic", "Automatic"),
            ("manual", "Manual"),
        ],
        string="Calculation Method",
        default="manual",
        required=True,
        tracking=True,
    )

    status = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("calculated", "Calculated"),
            ("verified", "Verified"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
    )

    scope = fields.Selection(
        related="emission_factor_id.scope",
        string="Emission Scope",
        store=True,
        readonly=True,
    )

    notes = fields.Text(string="Notes")

    _sql_constraints = [
        (
            "source_record_key_unique",
            "unique(source_record_key)",
            "A carbon transaction already exists for this source record.",
        ),
    ]

    @api.depends(
        "activity_quantity",
        "emission_factor_id",
        "emission_factor_id.factor_value",
    )
    def _compute_calculated_emission(self):
        for transaction in self:
            if (
                transaction.activity_quantity > 0
                and transaction.emission_factor_id
            ):
                transaction.calculated_emission = round(
                    transaction.activity_quantity
                    * transaction.emission_factor_id.factor_value,
                    4,
                )
            else:
                transaction.calculated_emission = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if values.get("reference", _("New")) == _("New"):
                values["reference"] = (
                    self.env["ir.sequence"].next_by_code(
                        "ecopulse.carbon.transaction"
                    )
                    or _("New")
                )

        records = super().create(vals_list)

        for record in records:
            if record.calculated_emission > 0:
                record.status = "calculated"

        return records

    @api.constrains("activity_quantity")
    def _check_activity_quantity(self):
        for transaction in self:
            if transaction.activity_quantity <= 0:
                raise ValidationError(
                    "Activity quantity must be greater than zero."
                )

    def action_calculate(self):
        for transaction in self:
            if not transaction.emission_factor_id:
                raise ValidationError(
                    "Select an emission factor before calculating."
                )

            transaction._compute_calculated_emission()
            transaction.status = "calculated"

        return True

    def action_verify(self):
        for transaction in self:
            if transaction.calculated_emission <= 0:
                raise ValidationError(
                    "The calculated emission must be greater than zero."
                )

            transaction.status = "verified"

        return True

    def action_cancel(self):
        self.write({"status": "cancelled"})
        return True

    def action_reset_to_draft(self):
        self.write({"status": "draft"})
        return True