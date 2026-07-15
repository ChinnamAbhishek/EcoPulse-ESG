# -*- coding: utf-8 -*-

from odoo import api, fields, models


class EcoPulseCarbonTransactionTrust(models.Model):
    """
    Extends the existing carbon transaction model with:

    1. Evidence tracking
    2. Carbon Trust Score
    3. Greenwashing risk detection
    4. Automatic risk explanations
    """

    _inherit = "ecopulse.carbon.transaction"

    # ---------------------------------------------------------
    # Evidence Information
    # ---------------------------------------------------------

    evidence_reference = fields.Char(
        string="Evidence Reference",
        help=(
            "Invoice number, meter-reading reference, fuel receipt, "
            "travel ticket number or other supporting reference."
        ),
        tracking=True,
    )

    evidence_attachment_count = fields.Integer(
        string="Evidence Documents",
        default=0,
        help="Number of supporting documents attached to this transaction.",
        tracking=True,
    )

    evidence_status = fields.Selection(
        selection=[
            ("missing", "Missing"),
            ("partial", "Partial"),
            ("submitted", "Submitted"),
            ("verified", "Verified"),
        ],
        string="Evidence Status",
        default="missing",
        required=True,
        tracking=True,
    )

    evidence_verified_by_id = fields.Many2one(
        comodel_name="res.users",
        string="Evidence Verified By",
        readonly=True,
        tracking=True,
    )

    evidence_verified_date = fields.Datetime(
        string="Evidence Verified On",
        readonly=True,
        tracking=True,
    )

    # ---------------------------------------------------------
    # Emission Factor Reliability
    # ---------------------------------------------------------

    factor_source_type = fields.Selection(
        selection=[
            ("official", "Official Government Factor"),
            ("certified", "Certified Industry Factor"),
            ("supplier", "Supplier Provided Factor"),
            ("internal", "Internal Organization Factor"),
            ("manual", "Manually Entered Factor"),
        ],
        string="Factor Source Type",
        default="manual",
        required=True,
        tracking=True,
        help=(
            "Identifies the reliability of the emission factor used "
            "for calculating this carbon transaction."
        ),
    )

    factor_source_reference = fields.Char(
        string="Factor Source Reference",
        help=(
            "Reference URL, document number, authority name or "
            "publication used for the emission factor."
        ),
        tracking=True,
    )

    factor_publication_year = fields.Integer(
        string="Factor Publication Year",
        help="Publication year of the emission factor.",
        tracking=True,
    )

    # ---------------------------------------------------------
    # Greenwashing Risk Inputs
    # ---------------------------------------------------------

    previous_emission_value = fields.Float(
        string="Previous Comparable Emission",
        digits=(16, 4),
        help=(
            "Emission value from a previous comparable reporting "
            "period. It is used to detect suspicious reductions."
        ),
        tracking=True,
    )

    manual_adjustment_percent = fields.Float(
        string="Manual Adjustment %",
        digits=(16, 2),
        default=0.0,
        help=(
            "Manual percentage adjustment applied to the calculated "
            "emission result."
        ),
        tracking=True,
    )

    reduction_explanation = fields.Text(
        string="Reduction Explanation",
        help=(
            "Explanation for a major reduction compared with the "
            "previous comparable emission value."
        ),
        tracking=True,
    )

    # ---------------------------------------------------------
    # Automatically Calculated Trust Results
    # ---------------------------------------------------------

    carbon_trust_score = fields.Integer(
        string="Carbon Trust Score",
        compute="_compute_carbon_trust_analysis",
        store=True,
        help=(
            "Automatically calculated reliability score from 0 to 100. "
            "A higher score means the carbon data is more trustworthy."
        ),
    )

    carbon_trust_level = fields.Selection(
        selection=[
            ("very_low", "Very Low Trust"),
            ("low", "Low Trust"),
            ("medium", "Medium Trust"),
            ("high", "High Trust"),
            ("verified", "Verified Trust"),
        ],
        string="Trust Level",
        compute="_compute_carbon_trust_analysis",
        store=True,
    )

    greenwashing_risk_level = fields.Selection(
        selection=[
            ("low", "Low Risk"),
            ("medium", "Medium Risk"),
            ("high", "High Risk"),
            ("critical", "Critical Risk"),
        ],
        string="Greenwashing Risk",
        compute="_compute_carbon_trust_analysis",
        store=True,
    )

    greenwashing_risk_score = fields.Integer(
        string="Greenwashing Risk Score",
        compute="_compute_carbon_trust_analysis",
        store=True,
        help="Automatically calculated risk score from 0 to 100.",
    )

    trust_analysis_reasons = fields.Text(
        string="Trust Analysis",
        compute="_compute_carbon_trust_analysis",
        store=True,
        help=(
            "Automatically generated reasons explaining the trust "
            "score and greenwashing risk."
        ),
    )

    suspicious_reduction_percent = fields.Float(
        string="Detected Reduction %",
        compute="_compute_carbon_trust_analysis",
        store=True,
        digits=(16, 2),
    )

    requires_manual_review = fields.Boolean(
        string="Requires Manual Review",
        compute="_compute_carbon_trust_analysis",
        store=True,
    )

    # ---------------------------------------------------------
    # Trust Score Calculation
    # ---------------------------------------------------------

    @api.depends(
        "evidence_reference",
        "evidence_attachment_count",
        "evidence_status",
        "factor_source_type",
        "factor_source_reference",
        "factor_publication_year",
        "previous_emission_value",
        "calculated_emission",
        "manual_adjustment_percent",
        "reduction_explanation",
        "status",
    )
    def _compute_carbon_trust_analysis(self):
        current_year = fields.Date.today().year

        for record in self:
            trust_score = 100
            risk_score = 0
            reasons = []

            # -------------------------------------------------
            # 1. Evidence reliability
            # -------------------------------------------------

            if record.evidence_status == "missing":
                trust_score -= 30
                risk_score += 30
                reasons.append(
                    "Supporting evidence is missing."
                )

            elif record.evidence_status == "partial":
                trust_score -= 18
                risk_score += 18
                reasons.append(
                    "Only partial supporting evidence is available."
                )

            elif record.evidence_status == "submitted":
                trust_score -= 8
                risk_score += 5
                reasons.append(
                    "Evidence is submitted but not yet verified."
                )

            elif record.evidence_status == "verified":
                reasons.append(
                    "Supporting evidence has been verified."
                )

            if not record.evidence_reference:
                trust_score -= 8
                risk_score += 8
                reasons.append(
                    "Evidence reference number is not provided."
                )

            if record.evidence_attachment_count <= 0:
                trust_score -= 10
                risk_score += 10
                reasons.append(
                    "No supporting document count is recorded."
                )

            # -------------------------------------------------
            # 2. Emission factor reliability
            # -------------------------------------------------

            factor_scores = {
                "official": 0,
                "certified": 4,
                "supplier": 9,
                "internal": 15,
                "manual": 25,
            }

            factor_penalty = factor_scores.get(
                record.factor_source_type,
                25,
            )

            trust_score -= factor_penalty
            risk_score += factor_penalty

            if record.factor_source_type == "official":
                reasons.append(
                    "An official government emission factor is used."
                )

            elif record.factor_source_type == "certified":
                reasons.append(
                    "A certified industry emission factor is used."
                )

            elif record.factor_source_type == "supplier":
                reasons.append(
                    "The emission factor was provided by a supplier."
                )

            elif record.factor_source_type == "internal":
                reasons.append(
                    "An internally defined emission factor is used."
                )

            else:
                reasons.append(
                    "A manually entered emission factor is used."
                )

            if not record.factor_source_reference:
                trust_score -= 8
                risk_score += 8
                reasons.append(
                    "Emission factor source reference is missing."
                )

            if record.factor_publication_year:
                factor_age = (
                    current_year -
                    record.factor_publication_year
                )

                if factor_age > 5:
                    trust_score -= 10
                    risk_score += 10
                    reasons.append(
                        "The emission factor is more than five years old."
                    )

                elif factor_age > 2:
                    trust_score -= 4
                    risk_score += 4
                    reasons.append(
                        "The emission factor should be reviewed for freshness."
                    )
            else:
                trust_score -= 5
                risk_score += 5
                reasons.append(
                    "Emission factor publication year is missing."
                )

            # -------------------------------------------------
            # 3. Manual adjustment risk
            # -------------------------------------------------

            adjustment = abs(
                record.manual_adjustment_percent or 0.0
            )

            if adjustment > 30:
                trust_score -= 25
                risk_score += 30
                reasons.append(
                    "Manual adjustment exceeds 30 percent."
                )

            elif adjustment > 15:
                trust_score -= 15
                risk_score += 18
                reasons.append(
                    "A significant manual adjustment was applied."
                )

            elif adjustment > 5:
                trust_score -= 7
                risk_score += 8
                reasons.append(
                    "A moderate manual adjustment was applied."
                )

            # -------------------------------------------------
            # 4. Suspicious reduction detection
            # -------------------------------------------------

            reduction_percent = 0.0

            if (
                record.previous_emission_value > 0
                and record.calculated_emission >= 0
            ):
                reduction_percent = (
                    (
                        record.previous_emission_value
                        - record.calculated_emission
                    )
                    / record.previous_emission_value
                ) * 100

                reduction_percent = max(
                    0.0,
                    reduction_percent,
                )

                if reduction_percent >= 70:
                    trust_score -= 25
                    risk_score += 35
                    reasons.append(
                        "Emission reduction exceeds 70 percent "
                        "compared with the previous value."
                    )

                elif reduction_percent >= 50:
                    trust_score -= 18
                    risk_score += 25
                    reasons.append(
                        "Emission reduction exceeds 50 percent "
                        "compared with the previous value."
                    )

                elif reduction_percent >= 30:
                    trust_score -= 8
                    risk_score += 12
                    reasons.append(
                        "Emission reduction exceeds 30 percent "
                        "and should be reviewed."
                    )

                if (
                    reduction_percent >= 30
                    and not record.reduction_explanation
                ):
                    trust_score -= 12
                    risk_score += 18
                    reasons.append(
                        "A major reduction has no supporting explanation."
                    )

            # -------------------------------------------------
            # 5. Transaction verification status
            # -------------------------------------------------

            if record.status == "verified":
                trust_score += 5
                risk_score -= 5
                reasons.append(
                    "The carbon transaction is verified."
                )

            elif record.status == "calculated":
                trust_score -= 3
                risk_score += 3
                reasons.append(
                    "The transaction is calculated but not verified."
                )

            elif record.status == "draft":
                trust_score -= 12
                risk_score += 12
                reasons.append(
                    "The transaction is still in draft status."
                )

            elif record.status == "cancelled":
                trust_score -= 25
                risk_score += 20
                reasons.append(
                    "The carbon transaction is cancelled."
                )

            # Keep scores inside 0–100
            trust_score = int(
                max(0, min(100, trust_score))
            )

            risk_score = int(
                max(0, min(100, risk_score))
            )

            # Trust level
            if trust_score >= 90:
                trust_level = "verified"
            elif trust_score >= 75:
                trust_level = "high"
            elif trust_score >= 50:
                trust_level = "medium"
            elif trust_score >= 25:
                trust_level = "low"
            else:
                trust_level = "very_low"

            # Risk level
            if risk_score >= 75:
                risk_level = "critical"
            elif risk_score >= 50:
                risk_level = "high"
            elif risk_score >= 25:
                risk_level = "medium"
            else:
                risk_level = "low"

            requires_review = (
                risk_level in ("high", "critical")
                or trust_score < 50
                or reduction_percent >= 50
            )

            record.carbon_trust_score = trust_score
            record.carbon_trust_level = trust_level
            record.greenwashing_risk_score = risk_score
            record.greenwashing_risk_level = risk_level
            record.suspicious_reduction_percent = reduction_percent
            record.requires_manual_review = requires_review

            record.trust_analysis_reasons = (
                "\n".join(
                    f"• {reason}"
                    for reason in reasons
                )
                if reasons
                else "No significant reliability risks detected."
            )

    # ---------------------------------------------------------
    # Evidence Verification Actions
    # ---------------------------------------------------------

    def action_verify_evidence(self):
        for record in self:
            record.write({
                "evidence_status": "verified",
                "evidence_verified_by_id": self.env.user.id,
                "evidence_verified_date": fields.Datetime.now(),
            })

        return True

    def action_reset_evidence_verification(self):
        for record in self:
            record.write({
                "evidence_status": "submitted",
                "evidence_verified_by_id": False,
                "evidence_verified_date": False,
            })

        return True