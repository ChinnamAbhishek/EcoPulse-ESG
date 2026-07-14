from odoo import api, fields, models
from odoo.exceptions import ValidationError


class EcoPulseESGReportWizard(models.TransientModel):
    _name = "ecopulse.esg.report.wizard"
    _description = "EcoPulse ESG Report Wizard"

    start_date = fields.Date(
        string="Start Date",
        default=lambda self: fields.Date.start_of(
            fields.Date.context_today(self),
            "year",
        ),
        required=True,
    )

    end_date = fields.Date(
        string="End Date",
        default=fields.Date.context_today,
        required=True,
    )

    department_id = fields.Many2one(
        comodel_name="ecopulse.department",
        string="Department",
        ondelete="set null",
    )

    scope = fields.Selection(
        selection=[
            ("scope_1", "Scope 1"),
            ("scope_2", "Scope 2"),
            ("scope_3", "Scope 3"),
        ],
        string="Emission Scope",
    )

    transaction_status = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("calculated", "Calculated"),
            ("verified", "Verified"),
            ("cancelled", "Cancelled"),
        ],
        string="Transaction Status",
    )

    include_cancelled = fields.Boolean(
        string="Include Cancelled Transactions",
        default=False,
    )

    include_goals = fields.Boolean(
        string="Include Environmental Goals",
        default=True,
    )

    include_department_analysis = fields.Boolean(
        string="Include Department Analysis",
        default=True,
    )

    include_source_analysis = fields.Boolean(
        string="Include Source Analysis",
        default=True,
    )

    @api.constrains("start_date", "end_date")
    def _check_date_range(self):
        for wizard in self:
            if (
                wizard.start_date
                and wizard.end_date
                and wizard.start_date > wizard.end_date
            ):
                raise ValidationError(
                    "Start date cannot be later than end date."
                )

    def _get_transaction_domain(self):
        self.ensure_one()

        domain = [
            ("transaction_date", ">=", self.start_date),
            ("transaction_date", "<=", self.end_date),
        ]

        if self.department_id:
            domain.append(
                ("department_id", "=", self.department_id.id)
            )

        if self.scope:
            domain.append(("scope", "=", self.scope))

        if self.transaction_status:
            domain.append(
                ("status", "=", self.transaction_status)
            )
        elif not self.include_cancelled:
            domain.append(("status", "!=", "cancelled"))

        return domain

    def action_print_report(self):
        self.ensure_one()

        data = {
            "wizard_id": self.id,
            "start_date": fields.Date.to_string(
                self.start_date
            ),
            "end_date": fields.Date.to_string(
                self.end_date
            ),
            "department_id": (
                self.department_id.id
                if self.department_id
                else False
            ),
            "scope": self.scope or False,
            "transaction_status": (
                self.transaction_status or False
            ),
            "include_cancelled": self.include_cancelled,
            "include_goals": self.include_goals,
            "include_department_analysis": (
                self.include_department_analysis
            ),
            "include_source_analysis": (
                self.include_source_analysis
            ),
        }

        return self.env.ref(
            "ecopulse_esg.action_report_esg_summary"
        ).report_action(
            self,
            data=data,
        )


class EcoPulseESGSummaryReport(models.AbstractModel):
    _name = (
        "report.ecopulse_esg."
        "report_esg_summary_document"
    )
    _description = "EcoPulse ESG Summary PDF Report"

    @api.model
    def _get_report_values(
        self,
        docids,
        data=None,
    ):
        data = data or {}

        wizard_id = data.get("wizard_id")

        wizard = self.env[
            "ecopulse.esg.report.wizard"
        ].browse(wizard_id).exists()

        if not wizard:
            wizard = self.env[
                "ecopulse.esg.report.wizard"
            ].browse(docids).exists()[:1]

        if not wizard:
            raise ValidationError(
                "The ESG report wizard could not be found."
            )

        domain = wizard._get_transaction_domain()

        transactions = self.env[
            "ecopulse.carbon.transaction"
        ].search(
            domain,
            order="transaction_date asc, id asc",
        )

        goals = self.env[
            "ecopulse.environmental.goal"
        ]

        if wizard.include_goals:
            goal_domain = []

            if wizard.department_id:
                goal_domain.append(
                    (
                        "department_id",
                        "=",
                        wizard.department_id.id,
                    )
                )

            goals = goals.search(
                goal_domain,
                order="end_date asc, id asc",
            )

        total_emission = 0.0
        scope_totals = {
            "scope_1": 0.0,
            "scope_2": 0.0,
            "scope_3": 0.0,
        }

        status_counts = {
            "draft": 0,
            "calculated": 0,
            "verified": 0,
            "cancelled": 0,
        }

        monthly_map = {}
        department_map = {}
        source_map = {}

        for transaction in transactions:
            emission = (
                transaction.calculated_emission or 0.0
            )

            total_emission += emission

            if transaction.scope in scope_totals:
                scope_totals[
                    transaction.scope
                ] += emission

            if transaction.status in status_counts:
                status_counts[
                    transaction.status
                ] += 1

            if transaction.transaction_date:
                month_key = (
                    transaction.transaction_date.strftime(
                        "%Y-%m"
                    )
                )

                month_label = (
                    transaction.transaction_date.strftime(
                        "%b %Y"
                    )
                )

                if month_key not in monthly_map:
                    monthly_map[month_key] = {
                        "key": month_key,
                        "label": month_label,
                        "total": 0.0,
                    }

                monthly_map[
                    month_key
                ]["total"] += emission

            department = transaction.department_id

            department_key = department.id or 0
            department_name = (
                department.name
                if department
                else "Not Assigned"
            )

            if department_key not in department_map:
                department_map[department_key] = {
                    "id": department_key,
                    "name": department_name,
                    "total": 0.0,
                    "transactions": 0,
                }

            department_map[
                department_key
            ]["total"] += emission

            department_map[
                department_key
            ]["transactions"] += 1

            source_key = (
                transaction.source_module or "manual"
            )

            source_label = dict(
                transaction._fields[
                    "source_module"
                ].selection
            ).get(
                source_key,
                "Manual",
            )

            if source_key not in source_map:
                source_map[source_key] = {
                    "key": source_key,
                    "label": source_label,
                    "total": 0.0,
                    "transactions": 0,
                }

            source_map[source_key]["total"] += emission
            source_map[
                source_key
            ]["transactions"] += 1

        monthly_emissions = sorted(
            monthly_map.values(),
            key=lambda item: item["key"],
        )

        department_ranking = sorted(
            department_map.values(),
            key=lambda item: item["total"],
            reverse=True,
        )

        source_analysis = sorted(
            source_map.values(),
            key=lambda item: item["total"],
            reverse=True,
        )

        for scope_key in scope_totals:
            if total_emission:
                scope_totals[
                    f"{scope_key}_percentage"
                ] = round(
                    (
                        scope_totals[scope_key]
                        / total_emission
                    )
                    * 100,
                    2,
                )
            else:
                scope_totals[
                    f"{scope_key}_percentage"
                ] = 0.0

        completed_goals = goals.filtered(
            lambda goal: goal.status == "completed"
        )

        active_goals = goals.filtered(
            lambda goal: goal.status == "active"
        )

        at_risk_goals = goals.filtered(
            lambda goal: goal.status == "at_risk"
        )

        average_goal_progress = (
            sum(
                goals.mapped(
                    "progress_percentage"
                )
            )
            / len(goals)
            if goals
            else 0.0
        )

        company = self.env.company

        return {
            "doc_ids": wizard.ids,
            "doc_model": (
                "ecopulse.esg.report.wizard"
            ),
            "docs": wizard,
            "company": company,
            "wizard": wizard,
            "transactions": transactions,
            "goals": goals,
            "total_emission": round(
                total_emission,
                2,
            ),
            "scope_totals": scope_totals,
            "status_counts": status_counts,
            "monthly_emissions": monthly_emissions,
            "department_ranking": (
                department_ranking
            ),
            "source_analysis": source_analysis,
            "completed_goals": len(
                completed_goals
            ),
            "active_goals": len(active_goals),
            "at_risk_goals": len(
                at_risk_goals
            ),
            "average_goal_progress": round(
                average_goal_progress,
                2,
            ),
            "generated_on": fields.Datetime.now(),
        }