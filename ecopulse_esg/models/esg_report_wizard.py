# -*- coding: utf-8 -*-

from collections import defaultdict
from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from . import esg_report_wizard

class EcoPulseESGReportWizard(models.TransientModel):
    _name = "ecopulse.esg.report.wizard"
    _description = "EcoPulse ESG Report Wizard"

    start_date = fields.Date(
        string="Start Date",
        required=True,
        default=lambda self: fields.Date.context_today(self).replace(
            month=1,
            day=1,
        ),
    )

    end_date = fields.Date(
        string="End Date",
        required=True,
        default=fields.Date.context_today,
    )

    department_id = fields.Many2one(
        comodel_name="ecopulse.department",
        string="Department",
        help="Leave empty to include all departments.",
    )

    scope = fields.Selection(
        selection=[
            ("scope_1", "Scope 1"),
            ("scope_2", "Scope 2"),
            ("scope_3", "Scope 3"),
        ],
        string="Emission Scope",
        help="Leave empty to include all emission scopes.",
    )

    transaction_status = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("calculated", "Calculated"),
            ("verified", "Verified"),
            ("cancelled", "Cancelled"),
        ],
        string="Transaction Status",
        help="Leave empty to include all permitted transaction statuses.",
    )

    include_cancelled = fields.Boolean(
        string="Include Cancelled Transactions",
        default=False,
        help=(
            "When enabled, cancelled transactions are included when "
            "no particular transaction status is selected."
        ),
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
                    _("Start Date cannot be later than End Date.")
                )

    def _get_transaction_domain(self):
        self.ensure_one()

        domain = []

        if self.start_date:
            domain.append(
                ("transaction_date", ">=", self.start_date)
            )

        if self.end_date:
            domain.append(
                ("transaction_date", "<=", self.end_date)
            )

        if self.department_id:
            domain.append(
                ("department_id", "=", self.department_id.id)
            )

        if self.scope:
            domain.append(
                ("scope", "=", self.scope)
            )

        if self.transaction_status:
            domain.append(
                ("status", "=", self.transaction_status)
            )
        elif not self.include_cancelled:
            domain.append(
                ("status", "!=", "cancelled")
            )

        return domain

    def _get_goal_domain(self):
        self.ensure_one()

        domain = []

        if self.department_id:
            domain.append(
                ("department_id", "=", self.department_id.id)
            )

        if self.start_date:
            domain.extend(
                [
                    "|",
                    ("end_date", "=", False),
                    ("end_date", ">=", self.start_date),
                ]
            )

        if self.end_date:
            domain.extend(
                [
                    "|",
                    ("start_date", "=", False),
                    ("start_date", "<=", self.end_date),
                ]
            )

        return domain

    def action_print_report(self):
        self.ensure_one()

        if self.start_date > self.end_date:
            raise UserError(
                _("Start Date cannot be later than End Date.")
            )

        report_action = self.env.ref(
            "ecopulse_esg.action_report_esg_summary",
            raise_if_not_found=False,
        )

        if not report_action:
            raise UserError(
                _(
                    "The ESG PDF report action was not found. "
                    "Please upgrade the EcoPulse ESG module."
                )
            )

        return report_action.report_action(self)


class EcoPulseESGSummaryReport(models.AbstractModel):
    _name = "report.ecopulse_esg.report_esg_summary_document"
    _description = "EcoPulse ESG Summary PDF Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard = self.env[
            "ecopulse.esg.report.wizard"
        ].browse(docids[:1])

        if not wizard.exists():
            raise UserError(
                _("The ESG report wizard record was not found.")
            )

        wizard.ensure_one()

        transaction_domain = wizard._get_transaction_domain()

        transactions = self.env[
            "ecopulse.carbon.transaction"
        ].search(
            transaction_domain,
            order="transaction_date asc, id asc",
        )

        goals = self.env[
            "ecopulse.environmental.goal"
        ].browse()

        if wizard.include_goals:
            goals = self.env[
                "ecopulse.environmental.goal"
            ].search(
                wizard._get_goal_domain(),
                order="end_date asc, id asc",
            )

        summary = self._prepare_summary(
            transactions=transactions,
            goals=goals,
        )

        scope_analysis = self._prepare_scope_analysis(
            transactions
        )

        status_analysis = self._prepare_status_analysis(
            transactions
        )

        monthly_analysis = self._prepare_monthly_analysis(
            transactions
        )

        department_analysis = []

        if wizard.include_department_analysis:
            department_analysis = (
                self._prepare_department_analysis(
                    transactions
                )
            )

        source_analysis = []

        if wizard.include_source_analysis:
            source_analysis = (
                self._prepare_source_analysis(
                    transactions
                )
            )

        goal_analysis = []

        if wizard.include_goals:
            goal_analysis = self._prepare_goal_analysis(
                goals
            )

        generated_on = fields.Datetime.context_timestamp(
            self,
            fields.Datetime.now(),
        )

        return {
            "doc_ids": wizard.ids,
            "doc_model": (
                "ecopulse.esg.report.wizard"
            ),
            "docs": wizard,

            "wizard": wizard,
            "transactions": transactions,
            "goals": goals,

            "summary": summary,
            "scope_analysis": scope_analysis,
            "status_analysis": status_analysis,
            "monthly_analysis": monthly_analysis,
            "department_analysis": department_analysis,
            "source_analysis": source_analysis,
            "goal_analysis": goal_analysis,

            "generated_on": generated_on,
            "generated_on_display": (
                generated_on.strftime(
                    "%d %B %Y, %I:%M %p"
                )
                if generated_on
                else ""
            ),

            "company": self.env.company,
            "currency": self.env.company.currency_id,

            "format_number": self._format_number,
            "get_scope_label": self._get_scope_label,
            "get_status_label": self._get_status_label,
            "get_source_label": self._get_source_label,
            "get_goal_status_label": (
                self._get_goal_status_label
            ),
            "get_metric_label": self._get_metric_label,
        }

    def _prepare_summary(self, transactions, goals):
        total_emissions = sum(
            float(
                transaction.calculated_emission or 0.0
            )
            for transaction in transactions
            if transaction.status != "cancelled"
        )

        verified_transactions = transactions.filtered(
            lambda transaction: (
                transaction.status == "verified"
            )
        )

        calculated_transactions = transactions.filtered(
            lambda transaction: (
                transaction.status == "calculated"
            )
        )

        draft_transactions = transactions.filtered(
            lambda transaction: (
                transaction.status == "draft"
            )
        )

        cancelled_transactions = transactions.filtered(
            lambda transaction: (
                transaction.status == "cancelled"
            )
        )

        active_goals = goals.filtered(
            lambda goal: goal.status == "active"
        )

        completed_goals = goals.filtered(
            lambda goal: goal.status == "completed"
        )

        at_risk_goals = goals.filtered(
            lambda goal: (
                goal.status == "at_risk"
                or goal.risk_level == "high"
            )
        )

        average_goal_progress = 0.0

        if goals:
            average_goal_progress = sum(
                float(goal.progress_percentage or 0.0)
                for goal in goals
            ) / len(goals)

        unique_departments = transactions.mapped(
            "department_id"
        )

        return {
            "transaction_count": len(transactions),

            "total_emissions": round(
                total_emissions,
                2,
            ),

            "verified_count": len(
                verified_transactions
            ),

            "calculated_count": len(
                calculated_transactions
            ),

            "draft_count": len(
                draft_transactions
            ),

            "cancelled_count": len(
                cancelled_transactions
            ),

            "department_count": len(
                unique_departments
            ),

            "goal_count": len(goals),

            "active_goal_count": len(
                active_goals
            ),

            "completed_goal_count": len(
                completed_goals
            ),

            "at_risk_goal_count": len(
                at_risk_goals
            ),

            "average_goal_progress": round(
                average_goal_progress,
                2,
            ),
        }

    def _prepare_scope_analysis(self, transactions):
        scope_totals = {
            "scope_1": {
                "key": "scope_1",
                "label": "Scope 1",
                "description": "Direct emissions",
                "transaction_count": 0,
                "total": 0.0,
                "percentage": 0.0,
            },
            "scope_2": {
                "key": "scope_2",
                "label": "Scope 2",
                "description": "Purchased energy emissions",
                "transaction_count": 0,
                "total": 0.0,
                "percentage": 0.0,
            },
            "scope_3": {
                "key": "scope_3",
                "label": "Scope 3",
                "description": "Value-chain emissions",
                "transaction_count": 0,
                "total": 0.0,
                "percentage": 0.0,
            },
        }

        total_emissions = 0.0

        for transaction in transactions:
            if transaction.status == "cancelled":
                continue

            scope = transaction.scope

            if scope not in scope_totals:
                continue

            emission = float(
                transaction.calculated_emission or 0.0
            )

            scope_totals[scope][
                "transaction_count"
            ] += 1

            scope_totals[scope]["total"] += emission

            total_emissions += emission

        for scope_data in scope_totals.values():
            scope_data["total"] = round(
                scope_data["total"],
                2,
            )

            if total_emissions:
                scope_data["percentage"] = round(
                    (
                        scope_data["total"]
                        / total_emissions
                    )
                    * 100,
                    2,
                )

        return list(scope_totals.values())

    def _prepare_status_analysis(self, transactions):
        status_data = {
            "draft": {
                "key": "draft",
                "label": "Draft",
                "count": 0,
                "total": 0.0,
            },
            "calculated": {
                "key": "calculated",
                "label": "Calculated",
                "count": 0,
                "total": 0.0,
            },
            "verified": {
                "key": "verified",
                "label": "Verified",
                "count": 0,
                "total": 0.0,
            },
            "cancelled": {
                "key": "cancelled",
                "label": "Cancelled",
                "count": 0,
                "total": 0.0,
            },
        }

        for transaction in transactions:
            status = transaction.status or "draft"

            if status not in status_data:
                continue

            status_data[status]["count"] += 1

            status_data[status]["total"] += float(
                transaction.calculated_emission or 0.0
            )

        result = []

        for item in status_data.values():
            item["total"] = round(
                item["total"],
                2,
            )

            result.append(item)

        return result

    def _prepare_monthly_analysis(self, transactions):
        monthly_totals = defaultdict(
            lambda: {
                "transaction_count": 0,
                "total": 0.0,
            }
        )

        for transaction in transactions:
            if (
                transaction.status == "cancelled"
                or not transaction.transaction_date
            ):
                continue

            month_key = transaction.transaction_date.strftime(
                "%Y-%m"
            )

            monthly_totals[month_key][
                "transaction_count"
            ] += 1

            monthly_totals[month_key]["total"] += float(
                transaction.calculated_emission or 0.0
            )

        result = []

        for month_key in sorted(monthly_totals):
            year, month = month_key.split("-")

            month_date = datetime(
                int(year),
                int(month),
                1,
            )

            values = monthly_totals[month_key]

            result.append(
                {
                    "key": month_key,
                    "label": month_date.strftime(
                        "%B %Y"
                    ),
                    "short_label": month_date.strftime(
                        "%b %Y"
                    ),
                    "transaction_count": values[
                        "transaction_count"
                    ],
                    "total": round(
                        values["total"],
                        2,
                    ),
                }
            )

        return result

    def _prepare_department_analysis(
        self,
        transactions,
    ):
        department_totals = defaultdict(
            lambda: {
                "department_id": False,
                "name": "Not Assigned",
                "transaction_count": 0,
                "total": 0.0,
            }
        )

        for transaction in transactions:
            if transaction.status == "cancelled":
                continue

            department = transaction.department_id

            department_key = (
                department.id
                if department
                else 0
            )

            department_totals[department_key][
                "department_id"
            ] = (
                department.id
                if department
                else False
            )

            department_totals[department_key][
                "name"
            ] = (
                department.display_name
                if department
                else "Not Assigned"
            )

            department_totals[department_key][
                "transaction_count"
            ] += 1

            department_totals[department_key][
                "total"
            ] += float(
                transaction.calculated_emission or 0.0
            )

        result = []

        for department_data in department_totals.values():
            department_data["total"] = round(
                department_data["total"],
                2,
            )

            result.append(department_data)

        result.sort(
            key=lambda item: item["total"],
            reverse=True,
        )

        for index, department_data in enumerate(
            result,
            start=1,
        ):
            department_data["rank"] = index

        return result

    def _prepare_source_analysis(
        self,
        transactions,
    ):
        source_totals = defaultdict(
            lambda: {
                "key": "manual",
                "label": "Manual",
                "transaction_count": 0,
                "total": 0.0,
            }
        )

        for transaction in transactions:
            if transaction.status == "cancelled":
                continue

            source_key = (
                transaction.source_module
                or "manual"
            )

            source_totals[source_key]["key"] = (
                source_key
            )

            source_totals[source_key]["label"] = (
                self._get_source_label(source_key)
            )

            source_totals[source_key][
                "transaction_count"
            ] += 1

            source_totals[source_key]["total"] += float(
                transaction.calculated_emission or 0.0
            )

        result = []

        for source_data in source_totals.values():
            source_data["total"] = round(
                source_data["total"],
                2,
            )

            result.append(source_data)

        result.sort(
            key=lambda item: item["total"],
            reverse=True,
        )

        return result

    def _prepare_goal_analysis(self, goals):
        result = []

        for goal in goals:
            result.append(
                {
                    "id": goal.id,
                    "name": goal.name,
                    "department": (
                        goal.department_id.display_name
                        if goal.department_id
                        else "Not Assigned"
                    ),
                    "metric_type": goal.metric_type,
                    "metric_label": self._get_metric_label(
                        goal.metric_type
                    ),
                    "baseline_value": float(
                        goal.baseline_value or 0.0
                    ),
                    "target_value": float(
                        goal.target_value or 0.0
                    ),
                    "current_value": float(
                        goal.current_value or 0.0
                    ),
                    "progress_percentage": round(
                        float(
                            goal.progress_percentage
                            or 0.0
                        ),
                        2,
                    ),
                    "status": goal.status,
                    "status_label": (
                        self._get_goal_status_label(
                            goal.status
                        )
                    ),
                    "risk_level": goal.risk_level,
                    "start_date": goal.start_date,
                    "end_date": goal.end_date,
                }
            )

        return result

    @api.model
    def _format_number(self, value):
        try:
            return "{:,.2f}".format(
                float(value or 0.0)
            )
        except (TypeError, ValueError):
            return "0.00"

    @api.model
    def _get_scope_label(self, scope):
        labels = {
            "scope_1": "Scope 1",
            "scope_2": "Scope 2",
            "scope_3": "Scope 3",
        }

        return labels.get(
            scope,
            "Unspecified",
        )

    @api.model
    def _get_status_label(self, status):
        labels = {
            "draft": "Draft",
            "calculated": "Calculated",
            "verified": "Verified",
            "cancelled": "Cancelled",
        }

        return labels.get(
            status,
            "Unknown",
        )

    @api.model
    def _get_source_label(self, source):
        labels = {
            "purchase": "Purchase",
            "fleet": "Fleet",
            "manufacturing": "Manufacturing",
            "expense": "Expense",
            "electricity": "Electricity",
            "travel": "Travel",
            "waste": "Waste",
            "manual": "Manual",
        }

        return labels.get(
            source,
            str(source or "Manual").replace(
                "_",
                " ",
            ).title(),
        )

    @api.model
    def _get_goal_status_label(self, status):
        labels = {
            "draft": "Draft",
            "active": "Active",
            "completed": "Completed",
            "at_risk": "At Risk",
            "cancelled": "Cancelled",
        }

        return labels.get(
            status,
            "Unknown",
        )

    @api.model
    def _get_metric_label(self, metric):
        labels = {
            "emission_reduction": (
                "Emission Reduction"
            ),
            "renewable_energy": (
                "Renewable Energy"
            ),
            "waste_reduction": (
                "Waste Reduction"
            ),
            "water_conservation": (
                "Water Conservation"
            ),
            "energy_efficiency": (
                "Energy Efficiency"
            ),
            "other": "Other",
        }

        return labels.get(
            metric,
            str(metric or "Other").replace(
                "_",
                " ",
            ).title(),
        )