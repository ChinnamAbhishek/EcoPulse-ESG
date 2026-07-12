from odoo import api, fields, models
from odoo.exceptions import ValidationError


class EcoPulseDepartment(models.Model):
    _name = "ecopulse.department"
    _description = "EcoPulse ESG Department"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "total_esg_score desc, name"

    name = fields.Char(
        string="Department Name",
        required=True,
        tracking=True,
    )

    code = fields.Char(
        string="Department Code",
        required=True,
        copy=False,
        tracking=True,
    )

    department_head_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Department Head",
        tracking=True,
    )

    parent_department_id = fields.Many2one(
        comodel_name="ecopulse.department",
        string="Parent Department",
        ondelete="restrict",
    )

    child_department_ids = fields.One2many(
        comodel_name="ecopulse.department",
        inverse_name="parent_department_id",
        string="Child Departments",
    )

    employee_count = fields.Integer(
        string="Employee Count",
        compute="_compute_employee_count",
        store=True,
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

    environmental_score = fields.Float(
        string="Environmental Score",
        default=0.0,
        tracking=True,
    )

    social_score = fields.Float(
        string="Social Score",
        default=0.0,
        tracking=True,
    )

    governance_score = fields.Float(
        string="Governance Score",
        default=0.0,
        tracking=True,
    )

    environmental_weight = fields.Float(
        string="Environmental Weight (%)",
        default=40.0,
        required=True,
    )

    social_weight = fields.Float(
        string="Social Weight (%)",
        default=30.0,
        required=True,
    )

    governance_weight = fields.Float(
        string="Governance Weight (%)",
        default=30.0,
        required=True,
    )

    total_esg_score = fields.Float(
        string="Total ESG Score",
        compute="_compute_total_esg_score",
        store=True,
        tracking=True,
    )

    carbon_transaction_ids = fields.One2many(
        comodel_name="ecopulse.carbon.transaction",
        inverse_name="department_id",
        string="Carbon Transactions",
    )

    total_emissions = fields.Float(
        string="Total Emissions",
        compute="_compute_total_emissions",
        store=True,
        help="Total calculated emissions in kg CO2e.",
    )

    _sql_constraints = [
        (
            "department_code_unique",
            "unique(code)",
            "The department code must be unique.",
        ),
    ]

    @api.depends("department_head_id")
    def _compute_employee_count(self):
        Employee = self.env["hr.employee"]

        for department in self:
            # This initial implementation counts employees whose manager
            # is the selected department head.
            if department.department_head_id:
                department.employee_count = Employee.search_count([
                    ("parent_id", "=", department.department_head_id.id)
                ])
            else:
                department.employee_count = 0

    @api.depends(
        "environmental_score",
        "social_score",
        "governance_score",
        "environmental_weight",
        "social_weight",
        "governance_weight",
    )
    def _compute_total_esg_score(self):
        for department in self:
            total_weight = (
                department.environmental_weight
                + department.social_weight
                + department.governance_weight
            )

            if not total_weight:
                department.total_esg_score = 0.0
                continue

            department.total_esg_score = round(
                (
                    department.environmental_score
                    * department.environmental_weight
                    + department.social_score
                    * department.social_weight
                    + department.governance_score
                    * department.governance_weight
                )
                / total_weight,
                2,
            )

    @api.depends("carbon_transaction_ids.calculated_emission")
    def _compute_total_emissions(self):
        for department in self:
            department.total_emissions = sum(
                department.carbon_transaction_ids.mapped(
                    "calculated_emission"
                )
            )

    @api.constrains(
        "environmental_weight",
        "social_weight",
        "governance_weight",
    )
    def _check_esg_weights(self):
        for department in self:
            total = (
                department.environmental_weight
                + department.social_weight
                + department.governance_weight
            )

            if abs(total - 100.0) > 0.01:
                raise ValidationError(
                    "Environmental, Social and Governance weights "
                    "must total exactly 100%."
                )

    @api.constrains(
        "environmental_score",
        "social_score",
        "governance_score",
    )
    def _check_scores(self):
        for department in self:
            scores = [
                department.environmental_score,
                department.social_score,
                department.governance_score,
            ]

            if any(score < 0 or score > 100 for score in scores):
                raise ValidationError(
                    "Every ESG score must be between 0 and 100."
                )

    @api.constrains("parent_department_id")
    def _check_parent_department(self):
        if self._has_cycle():
            raise ValidationError(
                "A department hierarchy cannot contain a cycle."
            )

    def action_recalculate_environmental_score(self):
        """Simple working environmental-score calculation.

        Hackathon MVP formula:
        - Lower emissions produce a better base score.
        - Environmental-goal progress contributes to the final score.
        """

        Goal = self.env["ecopulse.environmental.goal"]

        for department in self:
            total_emissions = department.total_emissions

            # Simple normalized emission score for MVP.
            # You can replace this with organization-specific baselines later.
            emission_score = max(0.0, 100.0 - min(total_emissions / 100.0, 100.0))

            goals = Goal.search([
                ("department_id", "=", department.id),
                ("status", "!=", "cancelled"),
            ])

            goal_score = (
                sum(goals.mapped("progress_percentage")) / len(goals)
                if goals
                else 0.0
            )

            department.environmental_score = round(
                emission_score * 0.60 + goal_score * 0.40,
                2,
            )

        return True