# -*- coding: utf-8 -*-

from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class EcoPulseCarbonReductionSimulator(models.TransientModel):
    """
    What-if Carbon Reduction Simulator.

    This wizard analyses existing carbon transactions and estimates
    future emissions after applying proposed reduction percentages.
    """

    _name = "ecopulse.carbon.reduction.simulator"
    _description = "EcoPulse Carbon Reduction Simulator"

    # ---------------------------------------------------------
    # Simulation Filters
    # ---------------------------------------------------------

    name = fields.Char(
        string="Simulation Name",
        default="Carbon Reduction Scenario",
        required=True,
    )

    start_date = fields.Date(
        string="Start Date",
        required=True,
        default=lambda self: fields.Date.today().replace(
            month=1,
            day=1,
        ),
    )

    end_date = fields.Date(
        string="End Date",
        required=True,
        default=fields.Date.today,
    )

    department_id = fields.Many2one(
        comodel_name="ecopulse.department",
        string="Department",
        help="Leave empty to simulate emissions for all departments.",
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

    include_draft = fields.Boolean(
        string="Include Draft Transactions",
        default=False,
    )

    # ---------------------------------------------------------
    # Reduction Scenario Inputs
    # ---------------------------------------------------------

    electricity_reduction_percent = fields.Float(
        string="Electricity Reduction %",
        default=0.0,
        help=(
            "Expected reduction in electricity-related emissions."
        ),
    )

    fuel_reduction_percent = fields.Float(
        string="Fuel Reduction %",
        default=0.0,
        help="Expected reduction in fuel-related emissions.",
    )

    travel_reduction_percent = fields.Float(
        string="Business Travel Reduction %",
        default=0.0,
        help="Expected reduction in business-travel emissions.",
    )

    waste_reduction_percent = fields.Float(
        string="Waste Reduction %",
        default=0.0,
        help="Expected reduction in waste-related emissions.",
    )

    supplier_reduction_percent = fields.Float(
        string="Supplier Emission Reduction %",
        default=0.0,
        help=(
            "Expected reduction in supplier and value-chain emissions."
        ),
    )

    general_reduction_percent = fields.Float(
        string="General Reduction %",
        default=0.0,
        help=(
            "Reduction applied to transactions that do not match "
            "electricity, fuel, travel, waste or supplier categories."
        ),
    )

    # ---------------------------------------------------------
    # Simulation Results
    # ---------------------------------------------------------

    baseline_emission = fields.Float(
        string="Current Baseline Emission",
        digits=(16, 4),
        readonly=True,
    )

    projected_emission = fields.Float(
        string="Projected Emission",
        digits=(16, 4),
        readonly=True,
    )

    emission_savings = fields.Float(
        string="Expected Emission Savings",
        digits=(16, 4),
        readonly=True,
    )

    overall_reduction_percent = fields.Float(
        string="Overall Reduction %",
        digits=(16, 2),
        readonly=True,
    )

    transaction_count = fields.Integer(
        string="Transactions Analysed",
        readonly=True,
    )

    electricity_baseline = fields.Float(
        string="Electricity Baseline",
        digits=(16, 4),
        readonly=True,
    )

    fuel_baseline = fields.Float(
        string="Fuel Baseline",
        digits=(16, 4),
        readonly=True,
    )

    travel_baseline = fields.Float(
        string="Travel Baseline",
        digits=(16, 4),
        readonly=True,
    )

    waste_baseline = fields.Float(
        string="Waste Baseline",
        digits=(16, 4),
        readonly=True,
    )

    supplier_baseline = fields.Float(
        string="Supplier Baseline",
        digits=(16, 4),
        readonly=True,
    )

    general_baseline = fields.Float(
        string="Other Emission Baseline",
        digits=(16, 4),
        readonly=True,
    )

    scenario_rating = fields.Selection(
        selection=[
            ("minimal", "Minimal Impact"),
            ("moderate", "Moderate Impact"),
            ("strong", "Strong Impact"),
            ("excellent", "Excellent Impact"),
        ],
        string="Scenario Impact",
        readonly=True,
    )

    scenario_summary = fields.Text(
        string="Simulation Summary",
        readonly=True,
    )

    recommendation_text = fields.Text(
        string="Smart Recommendations",
        readonly=True,
    )

    simulation_completed = fields.Boolean(
        string="Simulation Completed",
        readonly=True,
        default=False,
    )

    # ---------------------------------------------------------
    # Constraints
    # ---------------------------------------------------------

    @api.constrains(
        "start_date",
        "end_date",
    )
    def _check_simulation_dates(self):
        for wizard in self:
            if (
                wizard.start_date
                and wizard.end_date
                and wizard.start_date > wizard.end_date
            ):
                raise ValidationError(
                    "Start Date cannot be later than End Date."
                )

    @api.constrains(
        "electricity_reduction_percent",
        "fuel_reduction_percent",
        "travel_reduction_percent",
        "waste_reduction_percent",
        "supplier_reduction_percent",
        "general_reduction_percent",
    )
    def _check_reduction_percentages(self):
        fields_to_validate = [
            "electricity_reduction_percent",
            "fuel_reduction_percent",
            "travel_reduction_percent",
            "waste_reduction_percent",
            "supplier_reduction_percent",
            "general_reduction_percent",
        ]

        for wizard in self:
            for field_name in fields_to_validate:
                percentage = wizard[field_name] or 0.0

                if percentage < 0 or percentage > 100:
                    field_label = wizard._fields[
                        field_name
                    ].string

                    raise ValidationError(
                        f"{field_label} must be between 0 and 100."
                    )

    # ---------------------------------------------------------
    # Helper Methods
    # ---------------------------------------------------------

    def _get_transaction_domain(self):
        self.ensure_one()

        domain = [
            ("transaction_date", ">=", self.start_date),
            ("transaction_date", "<=", self.end_date),
            ("status", "!=", "cancelled"),
        ]

        if not self.include_draft:
            domain.append(
                ("status", "in", ["calculated", "verified"])
            )

        if self.department_id:
            domain.append(
                ("department_id", "=", self.department_id.id)
            )

        if self.scope:
            domain.append(
                ("scope", "=", self.scope)
            )

        return domain

    @staticmethod
    def _detect_emission_category(transaction):
        """
        Detect an emission category using available transaction text.

        This avoids depending on one exact source-module selection value.
        """

        searchable_values = [
            transaction.source_module or "",
            transaction.source_record_reference or "",
            transaction.activity_unit or "",
        ]

        if transaction.emission_factor_id:
            searchable_values.append(
                transaction.emission_factor_id.display_name or ""
            )

        searchable_text = " ".join(
            searchable_values
        ).lower()

        electricity_keywords = [
            "electric",
            "electricity",
            "power",
            "energy",
            "grid",
            "kwh",
        ]

        fuel_keywords = [
            "fuel",
            "diesel",
            "petrol",
            "gasoline",
            "natural gas",
            "lpg",
            "vehicle",
        ]

        travel_keywords = [
            "travel",
            "flight",
            "airline",
            "hotel",
            "taxi",
            "train",
            "business trip",
        ]

        waste_keywords = [
            "waste",
            "landfill",
            "recycle",
            "recycling",
            "disposal",
        ]

        supplier_keywords = [
            "supplier",
            "vendor",
            "procurement",
            "purchase",
            "supply chain",
            "value chain",
        ]

        if any(
            keyword in searchable_text
            for keyword in electricity_keywords
        ):
            return "electricity"

        if any(
            keyword in searchable_text
            for keyword in fuel_keywords
        ):
            return "fuel"

        if any(
            keyword in searchable_text
            for keyword in travel_keywords
        ):
            return "travel"

        if any(
            keyword in searchable_text
            for keyword in waste_keywords
        ):
            return "waste"

        if any(
            keyword in searchable_text
            for keyword in supplier_keywords
        ):
            return "supplier"

        return "general"

    def _get_category_reduction_percent(self, category):
        self.ensure_one()

        percentage_map = {
            "electricity": (
                self.electricity_reduction_percent
            ),
            "fuel": self.fuel_reduction_percent,
            "travel": self.travel_reduction_percent,
            "waste": self.waste_reduction_percent,
            "supplier": self.supplier_reduction_percent,
            "general": self.general_reduction_percent,
        }

        return percentage_map.get(category, 0.0) or 0.0

    # ---------------------------------------------------------
    # Main Simulation Action
    # ---------------------------------------------------------

    def action_run_simulation(self):
        self.ensure_one()

        transactions = self.env[
            "ecopulse.carbon.transaction"
        ].search(
            self._get_transaction_domain()
        )

        category_totals = {
            "electricity": 0.0,
            "fuel": 0.0,
            "travel": 0.0,
            "waste": 0.0,
            "supplier": 0.0,
            "general": 0.0,
        }

        projected_total = 0.0

        for transaction in transactions:
            emission = (
                transaction.calculated_emission or 0.0
            )

            category = self._detect_emission_category(
                transaction
            )

            category_totals[category] += emission

            reduction_percent = (
                self._get_category_reduction_percent(
                    category
                )
            )

            projected_emission = emission * (
                1 - reduction_percent / 100
            )

            projected_total += projected_emission

        baseline_total = sum(
            category_totals.values()
        )

        emission_savings = max(
            0.0,
            baseline_total - projected_total,
        )

        overall_reduction = (
            emission_savings / baseline_total * 100
            if baseline_total > 0
            else 0.0
        )

        if overall_reduction >= 30:
            scenario_rating = "excellent"
        elif overall_reduction >= 20:
            scenario_rating = "strong"
        elif overall_reduction >= 10:
            scenario_rating = "moderate"
        else:
            scenario_rating = "minimal"

        recommendations = (
            self._generate_recommendations(
                category_totals,
                overall_reduction,
            )
        )

        summary_lines = [
            (
                f"Analysed {len(transactions)} carbon "
                "transactions."
            ),
            (
                f"Current baseline emission: "
                f"{baseline_total:,.2f} kg CO₂e."
            ),
            (
                f"Projected emission: "
                f"{projected_total:,.2f} kg CO₂e."
            ),
            (
                f"Expected emission savings: "
                f"{emission_savings:,.2f} kg CO₂e."
            ),
            (
                f"Overall estimated reduction: "
                f"{overall_reduction:,.2f}%."
            ),
        ]

        self.write({
            "baseline_emission": baseline_total,
            "projected_emission": projected_total,
            "emission_savings": emission_savings,
            "overall_reduction_percent": overall_reduction,
            "transaction_count": len(transactions),
            "electricity_baseline": (
                category_totals["electricity"]
            ),
            "fuel_baseline": category_totals["fuel"],
            "travel_baseline": category_totals["travel"],
            "waste_baseline": category_totals["waste"],
            "supplier_baseline": (
                category_totals["supplier"]
            ),
            "general_baseline": category_totals["general"],
            "scenario_rating": scenario_rating,
            "scenario_summary": "\n".join(summary_lines),
            "recommendation_text": recommendations,
            "simulation_completed": True,
        })

        return {
            "type": "ir.actions.act_window",
            "name": "Carbon Reduction Simulator",
            "res_model": (
                "ecopulse.carbon.reduction.simulator"
            ),
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def _generate_recommendations(
        self,
        category_totals,
        overall_reduction,
    ):
        self.ensure_one()

        recommendations = []

        sorted_categories = sorted(
            category_totals.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        category_labels = {
            "electricity": "electricity consumption",
            "fuel": "fuel and vehicle usage",
            "travel": "business travel",
            "waste": "waste generation",
            "supplier": "supplier emissions",
            "general": "other operational emissions",
        }

        for category, total in sorted_categories[:3]:
            if total <= 0:
                continue

            reduction = (
                self._get_category_reduction_percent(
                    category
                )
            )

            label = category_labels[category]

            if reduction <= 0:
                recommendations.append(
                    f"• Add a reduction target for {label}; "
                    f"it currently contributes "
                    f"{total:,.2f} kg CO₂e."
                )
            elif reduction < 10:
                recommendations.append(
                    f"• Increase the proposed reduction for "
                    f"{label}; the current target is only "
                    f"{reduction:,.2f}%."
                )
            else:
                recommendations.append(
                    f"• Maintain the {reduction:,.2f}% "
                    f"reduction plan for {label} and assign "
                    "a responsible department owner."
                )

        if overall_reduction < 10:
            recommendations.append(
                "• The current scenario has limited impact. "
                "Consider stronger reduction targets for the "
                "highest-emission categories."
            )

        elif overall_reduction >= 30:
            recommendations.append(
                "• This is an ambitious scenario. Validate cost, "
                "timeline and operational feasibility before approval."
            )

        if not recommendations:
            recommendations.append(
                "• Add carbon transactions before running a "
                "meaningful reduction simulation."
            )

        return "\n".join(recommendations)

    # ---------------------------------------------------------
    # Reset Action
    # ---------------------------------------------------------

    def action_reset_simulation(self):
        self.ensure_one()

        self.write({
            "baseline_emission": 0.0,
            "projected_emission": 0.0,
            "emission_savings": 0.0,
            "overall_reduction_percent": 0.0,
            "transaction_count": 0,
            "electricity_baseline": 0.0,
            "fuel_baseline": 0.0,
            "travel_baseline": 0.0,
            "waste_baseline": 0.0,
            "supplier_baseline": 0.0,
            "general_baseline": 0.0,
            "scenario_rating": False,
            "scenario_summary": False,
            "recommendation_text": False,
            "simulation_completed": False,
        })

        return {
            "type": "ir.actions.act_window",
            "name": "Carbon Reduction Simulator",
            "res_model": (
                "ecopulse.carbon.reduction.simulator"
            ),
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }