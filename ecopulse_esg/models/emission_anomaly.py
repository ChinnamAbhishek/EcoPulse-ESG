# -*- coding: utf-8 -*-

from datetime import timedelta

from odoo import fields, models


class EcoPulseEmissionAnomaly(models.Model):
    """
    Extends carbon transactions with intelligent anomaly detection.

    The current transaction is compared with recent comparable
    transactions belonging to the same department, source and scope.
    """

    _inherit = "ecopulse.carbon.transaction"

    anomaly_status = fields.Selection(
        selection=[
            ("not_analyzed", "Not Analysed"),
            ("normal", "Normal"),
            ("warning", "Warning"),
            ("high", "High Anomaly"),
            ("critical", "Critical Anomaly"),
        ],
        string="Anomaly Status",
        default="not_analyzed",
        readonly=True,
        tracking=True,
        copy=False,
    )

    anomaly_score = fields.Integer(
        string="Anomaly Score",
        default=0,
        readonly=True,
        tracking=True,
        copy=False,
        help="Anomaly severity score from 0 to 100.",
    )

    historical_average_emission = fields.Float(
        string="Historical Average",
        digits=(16, 4),
        readonly=True,
        copy=False,
    )

    historical_maximum_emission = fields.Float(
        string="Historical Maximum",
        digits=(16, 4),
        readonly=True,
        copy=False,
    )

    anomaly_deviation_percent = fields.Float(
        string="Deviation from Average %",
        digits=(16, 2),
        readonly=True,
        copy=False,
    )

    anomaly_sample_count = fields.Integer(
        string="Historical Samples",
        readonly=True,
        copy=False,
    )

    anomaly_analysis_date = fields.Datetime(
        string="Analysed On",
        readonly=True,
        copy=False,
    )

    anomaly_analysis_reason = fields.Text(
        string="Anomaly Analysis",
        readonly=True,
        copy=False,
    )

    anomaly_requires_review = fields.Boolean(
        string="Anomaly Review Required",
        readonly=True,
        copy=False,
    )

    anomaly_reviewed = fields.Boolean(
        string="Anomaly Reviewed",
        default=False,
        tracking=True,
        copy=False,
    )

    anomaly_reviewed_by_id = fields.Many2one(
        comodel_name="res.users",
        string="Reviewed By",
        readonly=True,
        tracking=True,
        copy=False,
    )

    anomaly_reviewed_date = fields.Datetime(
        string="Reviewed On",
        readonly=True,
        tracking=True,
        copy=False,
    )

    anomaly_review_note = fields.Text(
        string="Review Note",
        tracking=True,
        copy=False,
    )

    def _get_anomaly_history_domain(self):
        self.ensure_one()

        analysis_date = (
            self.transaction_date
            or fields.Date.today()
        )

        history_start_date = analysis_date - timedelta(days=90)

        domain = [
            ("id", "!=", self.id),
            ("transaction_date", ">=", history_start_date),
            ("transaction_date", "<", analysis_date),
            ("status", "in", ["calculated", "verified"]),
            ("calculated_emission", ">", 0),
        ]

        if self.department_id:
            domain.append(
                (
                    "department_id",
                    "=",
                    self.department_id.id,
                )
            )

        if self.scope:
            domain.append(
                (
                    "scope",
                    "=",
                    self.scope,
                )
            )

        if self.source_module:
            domain.append(
                (
                    "source_module",
                    "=",
                    self.source_module,
                )
            )

        return domain

    def action_analyze_emission_anomaly(self):
        """
        Compare the current transaction against the previous 90 days.

        Classification:
        Below 30% deviation: Normal
        30% to 60% deviation: Warning
        60% to 100% deviation: High
        Above 100% deviation: Critical
        """

        for record in self:
            current_emission = (
                record.calculated_emission or 0.0
            )

            historical_transactions = self.search(
                record._get_anomaly_history_domain(),
                order="transaction_date desc",
                limit=50,
            )

            historical_values = [
                value
                for value in historical_transactions.mapped(
                    "calculated_emission"
                )
                if value and value > 0
            ]

            sample_count = len(historical_values)

            if current_emission <= 0:
                record.write({
                    "anomaly_status": "not_analyzed",
                    "anomaly_score": 0,
                    "historical_average_emission": 0.0,
                    "historical_maximum_emission": 0.0,
                    "anomaly_deviation_percent": 0.0,
                    "anomaly_sample_count": sample_count,
                    "anomaly_analysis_date": fields.Datetime.now(),
                    "anomaly_analysis_reason": (
                        "Anomaly analysis could not be completed "
                        "because the calculated emission is zero."
                    ),
                    "anomaly_requires_review": False,
                    "anomaly_reviewed": False,
                    "anomaly_reviewed_by_id": False,
                    "anomaly_reviewed_date": False,
                })

                continue

            if sample_count < 3:
                historical_average = (
                    sum(historical_values) / sample_count
                    if sample_count
                    else 0.0
                )

                historical_maximum = (
                    max(historical_values)
                    if historical_values
                    else 0.0
                )

                record.write({
                    "anomaly_status": "not_analyzed",
                    "anomaly_score": 0,
                    "historical_average_emission": historical_average,
                    "historical_maximum_emission": historical_maximum,
                    "anomaly_deviation_percent": 0.0,
                    "anomaly_sample_count": sample_count,
                    "anomaly_analysis_date": fields.Datetime.now(),
                    "anomaly_analysis_reason": (
                        "At least three comparable historical "
                        "transactions are required for reliable "
                        "anomaly detection."
                    ),
                    "anomaly_requires_review": False,
                    "anomaly_reviewed": False,
                    "anomaly_reviewed_by_id": False,
                    "anomaly_reviewed_date": False,
                })

                continue

            historical_average = (
                sum(historical_values) / sample_count
            )

            historical_maximum = max(historical_values)

            deviation_percent = (
                (
                    current_emission
                    - historical_average
                )
                / historical_average
                * 100
                if historical_average > 0
                else 0.0
            )

            positive_deviation = max(
                0.0,
                deviation_percent,
            )

            reasons = [
                (
                    f"Current emission is "
                    f"{current_emission:,.2f} kg CO₂e."
                ),
                (
                    f"Historical average is "
                    f"{historical_average:,.2f} kg CO₂e "
                    f"from {sample_count} comparable records."
                ),
                (
                    f"Deviation from historical average is "
                    f"{deviation_percent:,.2f}%."
                ),
            ]

            if positive_deviation >= 100:
                anomaly_status = "critical"

                anomaly_score = min(
                    100,
                    int(75 + positive_deviation / 10),
                )

                requires_review = True

                reasons.append(
                    "Critical anomaly detected. Current emissions "
                    "are more than double the recent average."
                )

            elif positive_deviation >= 60:
                anomaly_status = "high"

                anomaly_score = min(
                    89,
                    int(60 + positive_deviation / 8),
                )

                requires_review = True

                reasons.append(
                    "High anomaly detected. Emissions significantly "
                    "exceed the recent historical pattern."
                )

            elif positive_deviation >= 30:
                anomaly_status = "warning"

                anomaly_score = min(
                    69,
                    int(30 + positive_deviation / 3),
                )

                requires_review = True

                reasons.append(
                    "Warning anomaly detected. Emissions are "
                    "moderately above the recent average."
                )

            else:
                anomaly_status = "normal"

                anomaly_score = max(
                    0,
                    int(positive_deviation),
                )

                requires_review = False

                reasons.append(
                    "No significant upward emission anomaly "
                    "was detected."
                )

            if current_emission > historical_maximum:
                reasons.append(
                    "The current value exceeds the highest "
                    "comparable historical emission."
                )

                anomaly_score = min(
                    100,
                    anomaly_score + 10,
                )

                if anomaly_status == "normal":
                    anomaly_status = "warning"
                    requires_review = True

            if record.greenwashing_risk_level in (
                "high",
                "critical",
            ):
                reasons.append(
                    "The transaction also has elevated "
                    "greenwashing risk."
                )

                anomaly_score = min(
                    100,
                    anomaly_score + 10,
                )

                requires_review = True

            record.write({
                "anomaly_status": anomaly_status,
                "anomaly_score": anomaly_score,
                "historical_average_emission": historical_average,
                "historical_maximum_emission": historical_maximum,
                "anomaly_deviation_percent": deviation_percent,
                "anomaly_sample_count": sample_count,
                "anomaly_analysis_date": fields.Datetime.now(),
                "anomaly_analysis_reason": "\n".join(
                    f"• {reason}"
                    for reason in reasons
                ),
                "anomaly_requires_review": requires_review,
                "anomaly_reviewed": False,
                "anomaly_reviewed_by_id": False,
                "anomaly_reviewed_date": False,
            })

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Emission Anomaly Analysis",
                "message": (
                    "The transaction was compared with recent "
                    "historical emission data."
                ),
                "type": "success",
                "sticky": False,
            },
        }

    def action_mark_anomaly_reviewed(self):
        for record in self:
            record.write({
                "anomaly_reviewed": True,
                "anomaly_reviewed_by_id": self.env.user.id,
                "anomaly_reviewed_date": fields.Datetime.now(),
                "anomaly_requires_review": False,
            })

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Anomaly Reviewed",
                "message": (
                    "The emission anomaly has been marked "
                    "as reviewed."
                ),
                "type": "success",
                "sticky": False,
            },
        }

    def action_reset_anomaly_analysis(self):
        for record in self:
            record.write({
                "anomaly_status": "not_analyzed",
                "anomaly_score": 0,
                "historical_average_emission": 0.0,
                "historical_maximum_emission": 0.0,
                "anomaly_deviation_percent": 0.0,
                "anomaly_sample_count": 0,
                "anomaly_analysis_date": False,
                "anomaly_analysis_reason": False,
                "anomaly_requires_review": False,
                "anomaly_reviewed": False,
                "anomaly_reviewed_by_id": False,
                "anomaly_reviewed_date": False,
                "anomaly_review_note": False,
            })

        return True